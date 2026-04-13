module gray_threshold #(
    parameter TH_LOW  = 8'd80,
    parameter TH_HIGH = 8'd230
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        i_valid,
    input  wire        i_sof,
    input  wire        i_eol,
    input  wire        i_eof,
    input  wire [7:0]  i_gray,
    output reg         o_valid,
    output reg         o_sof,
    output reg         o_eol,
    output reg         o_eof,
    output reg         o_bin
);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            o_valid <= 1'b0;
            o_sof   <= 1'b0;
            o_eol   <= 1'b0;
            o_eof   <= 1'b0;
            o_bin   <= 1'b0;
        end else begin
            o_valid <= i_valid;
            o_sof   <= i_sof;
            o_eol   <= i_eol;
            o_eof   <= i_eof;

            if (i_valid) begin
                o_bin <= (i_gray >= TH_LOW) && (i_gray <= TH_HIGH);
            end
        end
    end

endmodule
