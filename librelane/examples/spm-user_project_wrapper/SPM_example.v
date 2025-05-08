// Copyright 2023 Efabless Corporation
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

// (Parameterized) Unsigned Serial/Parallel Multiplier:
// - Multiplicand x (Input bit-serially)
// - Multiplier a (All bits at the same time/Parallel)
// - Product y (Output bit-serial)

`default_nettype none
/*
 *-------------------------------------------------------------
 *
 * user_proj_example
 *
 * This is an example of a (trivially simple) user project,
 * showing how the user project can connect to the logic
 * analyzer, the wishbone bus, and the I/O pads.
 *
 * This project generates an integer count, which is output
 * on the user area GPIO pads (digital output only).  The
 * wishbone connection allows the project to be controlled
 * (start and stop) from the management SoC program.
 *
 * See the testbenches in directory "mprj_counter" for the
 * example programs that drive this user project.  The three
 * testbenches are "io_ports", "la_test1", and "la_test2".
 *
 *-------------------------------------------------------------
 */

module SPM_example #(
    parameter BITS = 32
)(
`ifdef USE_POWER_PINS
    inout vccd1,    // User area 1 1.8V supply
    inout vssd1,    // User area 1 digital ground
    // inout vdda2,
    // inout vssd2,
`endif

    // Wishbone Slave ports (WB MI A)
    input wb_clk_i,
    input wb_rst_i,
    input wbs_stb_i,
    input wbs_cyc_i,
    input wbs_we_i,
    input [3:0] wbs_sel_i,
    input [31:0] wbs_dat_i,
    input [31:0] wbs_adr_i,
    output reg wbs_ack_o,
    output reg [31:0] wbs_dat_o,

    // Logic Analyzer Signals
    input  [127:0] la_data_in,
    output [127:0] la_data_out,
    input  [127:0] la_oenb,

    // IOs
    input  wire [`MPRJ_IO_PADS-1:0] io_in,
    output wire [`MPRJ_IO_PADS-1:0] io_out,
    output wire [`MPRJ_IO_PADS-1:0] io_oeb,

    // IRQ
    output [2:0] irq
);
    wire clk;
    wire rst;
    

    wire [31:0] rdata; 
    wire [31:0] wdata;
    wire [BITS-1:0] count;

    wire valid;
    wire [3:0] wstrb;
    wire [31:0] la_write;

    //addresses for registers
    localparam X_OFF = 805306368, Y_OFF = 805306372, Y0_OFF = 805306376, Y1_OFF = 805306380, STAT_OFF = 32'h30000010;
    //states of the state machine
    localparam S0 = 0, S1 = 1, S2 = 2, S3 = 3;
    reg [3:0] STATE, nstate;
    reg [7:0] CNT, ncnt;
    //Registers for the multiplicand, multiplier, product
    reg [31:0] A, X;
    reg [63:0] Y0;
    wire status; // status register
    assign status = STATE == S0 ? 1:0; // if status reg == 1 means data is ready to be read or change the existing data
    //wire for the current product bit
    wire y;   
    //Registers for the WB bus
    reg [7:0] WB_address;
    reg WB_Read, WB_Write;

    // WB MI A
    assign valid = wbs_cyc_i && wbs_stb_i; 
    assign wstrb = wbs_sel_i & {4{wbs_we_i}};
    //assign wbs_dat_o = rdata;
    assign wdata = wbs_dat_i;

    // IO
    assign io_out = {(`MPRJ_IO_PADS){1'b0}};
    assign io_oeb = {(`MPRJ_IO_PADS){rst}};

    // IRQ
    assign irq = 3'b000;    // Unused

    // LA
    assign la_data_out = {(127){1'b0}};
    // Assuming LA probes [63:32] are for controlling the count register  
    assign la_write = ~la_oenb[63:32] & ~{BITS{valid}};
    // Assuming LA probes [65:64] are for controlling the count clk & reset  
    // assign clk = (~la_oenb[64]) ? la_data_in[64]: wb_clk_i;
    // assign rst = (~la_oenb[65]) ? la_data_in[65]: wb_rst_i;    
    assign clk = wb_clk_i;
    assign rst = wb_rst_i;

    always @(posedge clk or posedge rst) begin //assuming that we have posedge rst
        
        if(rst) begin
          A <= 32'b0;
          //wbs_ack_o <= 1'b0;
        end
        else if(valid && wbs_we_i && (wbs_adr_i==X_OFF)) begin
          A <= wbs_dat_i;
        //   wbs_dat_o <= A;
        //   wbs_ack_o <= 1'b1;
        end
    end
    
    always @(posedge clk or posedge rst) begin //assuming that we have posedge rst
        // wbs_ack_o <= 1'b0;
        if(rst) begin
            //wbs_ack_o <= 1'b0;  
            X <= 32'b0;
        end
        else if(STATE==S1) X <= X >>1; //shift right for the X since we always take the least significant bit in the multiplication
        else if(valid && wbs_we_i && (wbs_adr_i==Y_OFF)) begin //the reason we have a separate always block for the X is the shift right action
          X <= wbs_dat_i;
        //   wbs_dat_o <= X;
        //   wbs_ack_o <= 1'b1;
        end
        
    end

    always@(posedge clk) begin //a signal such as wbs_dat_o can be manipulated within one always block only
        if(valid && wbs_we_i && (wbs_adr_i==Y_OFF)) begin
            wbs_dat_o <= X;
        end
        else if(valid && wbs_we_i && (wbs_adr_i==X_OFF)) begin
            wbs_dat_o <= A;
        end
        else if(valid && !wbs_we_i && (wbs_adr_i==Y0_OFF)) begin
            wbs_dat_o <= Y0[31:0];
            // wbs_ack_o <= 1'b1;
        end 
        else if(valid && !wbs_we_i && (wbs_adr_i==Y1_OFF)) begin
          wbs_dat_o <= Y0[63:32];
        end
        else if(valid && !wbs_we_i && (wbs_adr_i==STAT_OFF)) begin
          wbs_dat_o <= status;
        end
    end

    always@(posedge clk) begin
        if(wbs_ack_o) begin
          wbs_ack_o <= 1'b0;
        end
        else if((valid && !wbs_we_i && (wbs_adr_i==Y1_OFF)) || (valid && !wbs_we_i && (wbs_adr_i==Y0_OFF)) || (valid && wbs_we_i && (wbs_adr_i==Y_OFF)) || (valid && wbs_we_i && (wbs_adr_i==X_OFF)) || (valid && !wbs_we_i && (wbs_adr_i==STAT_OFF))) begin
            wbs_ack_o <= 1'b1;
        end
    end

    always @(posedge clk or posedge rst) begin
        if(rst) begin
           Y0 <= 64'b0;
        end
        else if(STATE==S1) 
            Y0 <= {y, Y0[63:1]}; //taking the result from the SPM and shifting it right one bit at a time

    end

    always @(posedge clk or posedge rst) begin
        if(rst) begin
          STATE <= S0;
        end
        else 
            STATE <=nstate; //moving to the next state each clk cycle or on rst
    end

    always @(*) begin
        case(STATE) 
            S0: if(valid && wbs_we_i && (wbs_adr_i==Y_OFF)) nstate=S1; else nstate=S0;
            S1: if(CNT==64) nstate=S0; else nstate=S1;  //state 1 means that both numbers are ready now.
            default: nstate=S0; 
        endcase
    end

    always @(posedge clk or posedge rst) begin
        if(rst) begin
          CNT <= 8'b0;
        end
        else 
            CNT <= ncnt;
    end

    always @(*) begin
        ncnt = 0;
        if(CNT==64) ncnt <=0;
        else if(STATE==S1) ncnt = CNT + 1;
    end
    spm spm(.clk(clk), .rst(!rst), .a(A), .x(X[0]), .y(y));
    

endmodule

// (Parameterized) Unsigned Serial/Parallel Multiplier:
// - Multiplicand x (Input bit-serially)
// - Multiplier a (All bits at the same time/Parallel)
// - Product y (Output bit-serial)
module spm #(parameter bits=32) (
    input clk,
    input rst,
    input x,
    input[bits-1: 0] a,
    output y
);
    wire[bits: 0] y_chain;
    assign y_chain[0] = 0;
    assign y = y_chain[bits];

    wire[bits-1:0] a_flip;
    genvar i;
    generate 
        for (i = 0; i < bits; i = i + 1) begin : flip_block
            assign a_flip[i] = a[bits - i - 1];
        end 
    endgenerate

    delayed_serial_adder dsa[bits-1:0](
        .clk(clk),
        .rst(rst),
        .x(x),
        .a(a_flip),
        .y_in(y_chain[bits-1:0]),
        .y_out(y_chain[bits:1])
    );

endmodule

module delayed_serial_adder(
    input clk,
    input rst,
    input x,
    input a,
    input y_in,
    output reg y_out
);
    reg last_carry;
    wire last_carry_next;
    wire y_out_next;

    wire g = x & a;
    assign {last_carry_next, y_out_next} = g + y_in + last_carry;

    always @ (posedge clk or negedge rst) begin
        if (!rst) begin
            last_carry <= 1'b0;
            y_out <= 1'b0;
        end else begin
            last_carry <= last_carry_next;
            y_out <= y_out_next;
        end
    end
endmodule
