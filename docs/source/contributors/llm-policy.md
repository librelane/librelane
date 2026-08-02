# Large Language Model Contribution Policy

**tl;dr** is LibreLane is a small, focused project with limited maintenance
bandwidth, thus:

* We reject "agentic" or vibe-coded submissions.
* For smaller issues found using LLMs, we encourage you to submit bug reports
  instead where the maintainers can fix them.
* For high-quality code that is primarily human-authored but AI-assisted, we
  require an `Assisted-by` (**not** `Co-authored-by`) commit trailer.
* Do not use LLMs for communication, *with a narrow exemption* if English is not
  your native language, in which case, you are allowed to translate text you
  have written yourself.

```{note}
Contributions submitted before the adoption of this Policy will be reviewed in
good faith.
```

## Impetus and Rationale

The impetus is to decrease the maintainership burden from large language model
(LLM)-generated code or prose. LibreLane is mostly run by volunteers and we have
found that unchecked LLM-generated contributions, be they issues or
pull-requests, time-intensive on our side *at best*. Sometimes, valid points
have been raised, but a one-paragraph human-authored response would have
sufficed versus a wall of LLM prose. Other times, we spent a good hour
performing unpaid code review for unmergeable code in pursuit of fairness to
contributors.

We state that we strongly prefer all contributions to be as humanly-authored as
possible, considering a number of externalities related to the AI industry.
Nonetheless, we concede a blanket ban on LLM-aided contributions would be
burdensome and likely unenforceable.

It is for this reason we simply define the scope of LLM contributions and
encourage transparency.

## Scope

LibreLane's LLM policy (the Policy) applies to any and all of the following
items hosted under the https://github.com/librelane/librelane namespace

* Code
* Documentation

…and any communication hosted either under said namespace or the
[#librelane:fossi-chat.org](https://matrix.to/#/#librelane:fossi-chat.org)
Matrix channel.

## Code Contributions

Broadly, the maintainers decline "vibe-coded" contributions, whether fully
automated ("agentic") or human-curated. Contributions must be based on a
understanding of the codebase and you must be able to faithfully answer
questions by maintainers on why any or all decisions was taken. Telltale signs 
we have historically encountered of vibe-coded contributions include but are not
limited to:

- Major code duplication of existing functions
- Code duplication within the contribution
- Bespoke implementation of complex functionality where code reuse from a PyPI
  library or similar would be more appropriate
- Untested bugfixes that ignore the context of a certain piece of code
- Redundant or overly verbose comments

An exemption from this Policy is provided for the use of text transformation
tooling to produce changes that the author manually reviews and understands,
including inline "auto‐completion" (even if LLM‐based) of short, rote snippets
of text that do not contribute anything beyond boilerplate the author would have
written anyway.

For contributions that are merely AI-assisted, i.e., AI may have been used to
help with parts of the PR that can reasonably interpreted to not meet the
definition of
[Legal Significance](https://www.gnu.org/prep/maintain/maintain.html#Legally-Significant)
as described by GNU, is considered a "covered" use of LLMs, and maintainers may
at their discretion choose to accept it so long as it is appropriately labeled.

### Documentation

Any majorly LLM-generated articles or tutorials within the body of LibreLane's
documentation are not allowed.

Machine-translating non-English text to English is *partially* exempt from this
policy, in that we will require you to provide the original text and acknowledge
the use of machine translation. In all likelihood, it will require editorial
review by a maintainer, and we may choose to simply keep the tutorial in its
original language. We actually encourage you write tutorials in languages other
than English.

We would strongly prefer any documentation, including class and variable
documentation, to be in your own words, nonetheless because of the typical
terseness of said documentation, this is undetectable. We ask that you abide
by the transparency rules in the relevant commits.

### Communications

Communications include chat messages, bug reports, enhancement requests and pull
request bodies, as well as comments and replies to any of them.

We ask that you do not use an LLM to write your communications with other human
beings as a matter of mutual respect — a human will read it, so a human needs to
write it. We **do** provide an exception here if you're not a native English
speaker and you're using an LLM to **translate text you wrote yourself** in your
original language.

Any bugs found by an LLM must be independently confirmed by you before filing a
bug report. Lacking wider context, LLMs sometimes flag bugs that cannot be
triggered under normal circumstances or simply flag odd code that isn't
necessarily a bug but necessitated by weird behavior in underlying utilties or
operating systems.

Security incidents are exempt from this policy if it is somehow burdensome to
create a replicator.

## Transparency

All covered use of LLM-based tooling for a contribution must be disclosed as
part of that contribution.

In the case of LLM‐based AI tooling used for commits, this **must** be in the
form of an `Assisted-by:` Git commit trailer, including at least the tool name
and the primary model name and version used for the contribution.

A `Co-authored-by:` trailer does not satisfy this policy and commits with this
trailer for an LLM will be rejected: authorship is for legal attribution and
responsibility, which requires a human author.

Any adequate form of disclosure is permitted for other kinds of contributions.

## Further Exemptions

In addition to any previously stated exemptions, the following uses are also
considered exempt:

* Use of LLMs for research, testing, debugging, or private review is out of
  scope, if no substantial amount of their output is included in the resulting
  contribution.

* Use of LLMs to develop upstream software included with LibreLane is decidedly
  not in scope. If an upstream piece of software's code quality declines, we
  reserve the right to substitute or remove it independent of this policy.

* Any act that is mere *use* of LibreLane, including but not limited to:

  * Use of LLMs with LibreLane to make your own downstream chips.

  * Use of LLMs to generate your own custom
    {doc}`Plugins </usage/writing_plugins.md>` (not for upstreaming).

## Enforcement

If you believe that someone is using an LLM without appropriate disclosure and
review, you can politely ask them if that's the case and point them to this
Policy as appropriate.

Please assume good faith and remain civil; it's not always possible to
determine, and it is more likely that someone overlooked this Policy than
deliberately violated it.

If a maintainer judges that a contribution doesn't comply with this Policy,
they should paste the following response and, depending on the severity of the
violation, request changes or close the PR:

> This PR does not appear to comply with our policy on LLM contributions.
> Please see the relevant policy here:
> https://librelane.readthedocs.io/en/stable/contributors/llm-policy.html

Maintainers and other users are encouraged (as time allows) to guide said users
to rework their contributions in a manner more constructive to LibreLane, such
as by filing Policy-compliant bug reports or feature requests.

Repeated, deliberate violations of the policy may result in loss of contributing
privileges.

## Credits

Loosely based on a combination of these policies:

* [Contributing to Nixpkgs: Automation/AI Policy](https://github.com/NixOS/nixpkgs/blob/152483cfeaa117268568d42e431f4213f0095d28/CONTRIBUTING.md#automationai-policy)
* [LLVM AI Tool policy](https://llvm.org/docs/AIToolPolicy.html)
* [GCC AI policy](https://gcc.gnu.org/ai-policy.html)
