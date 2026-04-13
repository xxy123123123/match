module roi_bbox_accum #(
    parameter IMG_W = 1280,
    parameter IMG_H = 720,
    parameter MIN_W = 40,
    parameter MIN_H = 12
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         i_valid,
    input  wire         i_sof,
    input  wire         i_eol,
    input  wire         i_eof,
    input  wire         i_bin,
    output reg          o_bbox_valid,
    output reg [11:0]   o_x_min,
    output reg [11:0]   o_y_min,
    output reg [11:0]   o_x_max,
    output reg [11:0]   o_y_max
);

    reg [11:0] x_cnt;
    reg [11:0] y_cnt;
    reg [11:0] x_min;
    reg [11:0] y_min;
    reg [11:0] x_max;
    reg [11:0] y_max;
    reg        found;

    wire [11:0] box_w = (x_max >= x_min) ? (x_max - x_min + 12'd1) : 12'd0;
    wire [11:0] box_h = (y_max >= y_min) ? (y_max - y_min + 12'd1) : 12'd0;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            x_cnt <= 12'd0;
            y_cnt <= 12'd0;
            x_min <= 12'hfff;
            y_min <= 12'hfff;
            x_max <= 12'd0;
            y_max <= 12'd0;
            found <= 1'b0;

            o_bbox_valid <= 1'b0;
            o_x_min <= 12'd0;
            o_y_min <= 12'd0;
            o_x_max <= 12'd0;
            o_y_max <= 12'd0;
        end else begin
            o_bbox_valid <= 1'b0;

            if (i_sof) begin
                x_cnt <= 12'd0;
                y_cnt <= 12'd0;
                x_min <= 12'hfff;
                y_min <= 12'hfff;
                x_max <= 12'd0;
                y_max <= 12'd0;
                found <= 1'b0;
            end

            if (i_valid) begin
                if (i_bin) begin
                    found <= 1'b1;

                    if (x_cnt < x_min) x_min <= x_cnt;
                    if (y_cnt < y_min) y_min <= y_cnt;
                    if (x_cnt > x_max) x_max <= x_cnt;
                    if (y_cnt > y_max) y_max <= y_cnt;
                end

                if (i_eol) begin
                    x_cnt <= 12'd0;
                    if (y_cnt < IMG_H - 1) begin
                        y_cnt <= y_cnt + 12'd1;
                    end
                end else if (x_cnt < IMG_W - 1) begin
                    x_cnt <= x_cnt + 12'd1;
                end
            end

            if (i_eof) begin
                if (found && (box_w >= MIN_W) && (box_h >= MIN_H)) begin
                    o_bbox_valid <= 1'b1;
                    o_x_min <= x_min;
                    o_y_min <= y_min;
                    o_x_max <= x_max;
                    o_y_max <= y_max;
                end
            end
        end
    end

endmodule
