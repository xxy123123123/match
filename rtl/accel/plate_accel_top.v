module plate_accel_top #(
    parameter IMG_W   = 1280,
    parameter IMG_H   = 720,
    parameter TH_LOW  = 8'd80,
    parameter TH_HIGH = 8'd230,
    parameter MIN_W   = 40,
    parameter MIN_H   = 12
) (
    input  wire         clk,
    input  wire         rst_n,

    input  wire         i_valid,
    input  wire         i_sof,
    input  wire         i_eol,
    input  wire         i_eof,
    input  wire [7:0]   i_r,
    input  wire [7:0]   i_g,
    input  wire [7:0]   i_b,

    output wire         o_valid,
    output wire         o_sof,
    output wire         o_eol,
    output wire         o_eof,
    output wire [7:0]   o_gray,
    output wire         o_bin,

    output wire         o_bbox_valid,
    output wire [11:0]  o_x_min,
    output wire [11:0]  o_y_min,
    output wire [11:0]  o_x_max,
    output wire [11:0]  o_y_max
);

    wire        gray_valid;
    wire        gray_sof;
    wire        gray_eol;
    wire        gray_eof;
    wire [7:0]  gray_data;

    wire        bin_valid;
    wire        bin_sof;
    wire        bin_eol;
    wire        bin_eof;
    wire        bin_data;

    rgb2gray u_rgb2gray (
        .clk    (clk),
        .rst_n  (rst_n),
        .i_valid(i_valid),
        .i_sof  (i_sof),
        .i_eol  (i_eol),
        .i_eof  (i_eof),
        .i_r    (i_r),
        .i_g    (i_g),
        .i_b    (i_b),
        .o_valid(gray_valid),
        .o_sof  (gray_sof),
        .o_eol  (gray_eol),
        .o_eof  (gray_eof),
        .o_gray (gray_data)
    );

    gray_threshold #(
        .TH_LOW (TH_LOW),
        .TH_HIGH(TH_HIGH)
    ) u_gray_threshold (
        .clk    (clk),
        .rst_n  (rst_n),
        .i_valid(gray_valid),
        .i_sof  (gray_sof),
        .i_eol  (gray_eol),
        .i_eof  (gray_eof),
        .i_gray (gray_data),
        .o_valid(bin_valid),
        .o_sof  (bin_sof),
        .o_eol  (bin_eol),
        .o_eof  (bin_eof),
        .o_bin  (bin_data)
    );

    roi_bbox_accum #(
        .IMG_W (IMG_W),
        .IMG_H (IMG_H),
        .MIN_W (MIN_W),
        .MIN_H (MIN_H)
    ) u_roi_bbox_accum (
        .clk        (clk),
        .rst_n      (rst_n),
        .i_valid    (bin_valid),
        .i_sof      (bin_sof),
        .i_eol      (bin_eol),
        .i_eof      (bin_eof),
        .i_bin      (bin_data),
        .o_bbox_valid(o_bbox_valid),
        .o_x_min    (o_x_min),
        .o_y_min    (o_y_min),
        .o_x_max    (o_x_max),
        .o_y_max    (o_y_max)
    );

    assign o_valid = bin_valid;
    assign o_sof   = bin_sof;
    assign o_eol   = bin_eol;
    assign o_eof   = bin_eof;
    assign o_gray  = gray_data;
    assign o_bin   = bin_data;

endmodule
