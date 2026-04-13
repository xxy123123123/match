module rgb2gray #(
    parameter DW = 8
) (
    input  wire             clk,
    input  wire             rst_n,
    input  wire             i_valid,
    input  wire             i_sof,
    input  wire             i_eol,
    input  wire             i_eof,
    input  wire [DW-1:0]    i_r,
    input  wire [DW-1:0]    i_g,
    input  wire [DW-1:0]    i_b,
    output reg              o_valid,
    output reg              o_sof,
    output reg              o_eol,
    output reg              o_eof,
    output reg [DW-1:0]     o_gray
);

    reg [15:0] gray_mul;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            o_valid <= 1'b0;
            o_sof   <= 1'b0;
            o_eol   <= 1'b0;
            o_eof   <= 1'b0;
            o_gray  <= {DW{1'b0}};
            gray_mul <= 16'd0;
        end else begin
            o_valid <= i_valid;
            o_sof   <= i_sof;
            o_eol   <= i_eol;
            o_eof   <= i_eof;

            if (i_valid) begin
                // gray = 0.299R + 0.587G + 0.114B
                gray_mul <= (16'd77 * i_r) + (16'd150 * i_g) + (16'd29 * i_b);
                o_gray   <= gray_mul[15:8];
            end
        end
    end

endmodule
