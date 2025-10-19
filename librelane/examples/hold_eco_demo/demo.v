module hold_violation(
    input clk,
    input d,
    output q
);
    wire intermediate;
    wire clk_delayed;

    sky130_fd_sc_hd__clkbuf_4 dly (
        .A(clk),
        .X(clk_delayed)
    );

    sky130_fd_sc_hd__dfrtp_4 u_ff1 (
        .CLK(clk),
        .D(d),
        .RESET_B(1'b1),
        .Q(intermediate)
    );

    sky130_fd_sc_hd__dfrtp_1 u_ff2 (
        .CLK(clk_delayed),
        .D(intermediate),
        .RESET_B(1'b1),
        .Q(q)
    );
endmodule
