#!/usr/bin/env node
// Copyright 2023 Efabless Corporation
//
// Licensed under the Apache License, Version 2.0(the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
//     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
"use strict";

/**
 * @param {string} comparingDirectory
 * @param {string} againstBranch
 * @param {string} verbosity
 * @param {string} table_out
 * @param {string} token
 * @returns {string}
 */
function compareMetricsWithBranch({ comparingDirectory, againstBranch, verbosity, table_out = null, token = "" }) {
    const { spawnSync } = require("child_process");

    let tableOutOpts = table_out ? ["--table-out", table_out] : [];
    let allOpts = ["-m", "librelane.common.metrics", "compare-remote", comparingDirectory, "--branch", againstBranch, "--table-verbosity", verbosity,].concat(tableOutOpts)

    let child = spawnSync("python3", allOpts.concat(["--token", token]), { encoding: "utf8" });

    let result = "";
    if (child.status != 0) {
        throw new Error("Failed to create report: \n\n```\n" + child.stderr + "\n```");
    } else {
        result += "Metric comparisons are in beta. Please report bugs under the issues tab.\n---\n";
        result += `> To create this report yourself, grab the metrics artifact from the CI run, extract them, and invoke \`python3 ${allOpts.join(' ')}\`.\n\n` + child.stdout;
    }

    return result.trim();
};

/**
 * 
 * @param {Octokit} github 
 * @param {object} context 
 * @param {string} botUsername 
 * @param {string} body 
 */
async function postOrUpdateComment({ github, context, botUsername, body }) {
    const METRIC_REPORT_MARK = "<!-- MARK: METRICS REPORT -->";

    let page = 1;
    let allComments = [];
    let comments = [];
    do {
        let response = await github.request("GET /repos/{owner}/{repo}/issues/{issue_number}/comments?page={page}&per_page=100", {
            issue_number: context.issue.number,
            owner: context.repo.owner,
            repo: context.repo.repo,
            page,
        });
        comments = response.data;
        allComments = allComments.concat(comments);
        page += 1;
    } while (comments.length != 0);

    let found = null;
    for (let comment of allComments) {
        if (comment.body.includes(METRIC_REPORT_MARK) && comment.user.login == botUsername) {
            found = comment;
            break;
        }
    }

    let fn = github.rest.issues.createComment;
    let request = {
        issue_number: context.issue.number,
        owner: context.repo.owner,
        repo: context.repo.repo,
        body: `${METRIC_REPORT_MARK}\n\n${body}`
    };

    if (found) {
        request.comment_id = found.id;
        fn = github.rest.issues.updateComment;
    }

    await fn(request);
}

/**
 * 
 * @param {Octokit} github 
 * @param {object} context 
 * @param {string} botUsername 
 * @param {string} botToken 
 * @param {string} comparingDirectory
 * @param {string} againstBranch
 */
async function compareAndComment({ github, context, botUsername, botToken, comparingDirectory, againstBranch }) {
    const fs = require("fs");
    let body;
    try {
        body = compareMetricsWithBranch({ comparingDirectory, againstBranch, verbosity: "ALL", table_out: "./tables_all.md", token: botToken });
        let tables = fs.readFileSync("./tables_all.md", { encoding: "utf8" });

        let gistResponse = await github.rest.gists.create({
            public: true,
            description: `Results for ${context.repo.owner} / ${context.repo.repo}#${context.issue.number} (Run ${context.runId})`,
            files: {
                "10-ALL.md": {
                    content: tables
                }
            }
        });

        body += `\n\nFull tables ► ${gistResponse.data.html_url}\n`;
    } catch (e) {
        body = e.message;
        console.error(e.message)
    }

    await postOrUpdateComment({ github, context, botUsername, body })
}

module.exports = compareAndComment;

if (require.main === module) {
    // Test
    try {
        require("@octokit/rest");
        require("commander");
    } catch (error) {
        console.error("Run 'yarn add @octokit/rest @octokit/plugin-paginate-rest commander'")
        process.exit(-1);
    }
    const { Octokit } = require("@octokit/rest");
    const { Command } = require('commander');
    const script = new Command();

    script.command("comment")
        .argument("directory", "The directory containing the generated metrics to compare")
        .option("-i,--issue-number <issue-number>", "The number of the GitHub PR to comment on")
        .option("-b,--branch <branch>", "The branch to compare against")
        .option("-t,--token <token>", "The GitHub token to use")
        .action((directory, options) => {
            let octokit = new Octokit({
                auth: options.token,
            });

            const context = {
                repo: {
                    owner: "efabless",
                    repo: "librelane"
                },
                issue: {
                    number: options.issueNumber
                },
                runId: "api_test"
            };

            compareAndComment({
                github: octokit,
                context: context,
                botUsername: "librelane-bot",
                botToken: options.token,
                comparingDirectory: directory,
                againstBranch: options.branch
            });
        });

    script.parse();
}
