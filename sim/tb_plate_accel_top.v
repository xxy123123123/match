`timescale 1ns/1ps

module tb_plate_accel_top;

    localparam IMG_W = 16;
    localparam IMG_H = 12;

    reg         clk;
    reg         rst_n;
    reg         i_valid;
    reg         i_sof;
    reg         i_eol;
    reg         i_eof;
    reg [7:0]   i_r;
    reg [7:0]   i_g;
    reg [7:0]   i_b;

    wire        o_valid;
    wire        o_sof;
    wire        o_eol;
    wire        o_eof;
    wire [7:0]  o_gray;
    wire        o_bin;

    wire        o_bbox_valid;
    wire [11:0] o_x_min;
    wire [11:0] o_y_min;
    wire [11:0] o_x_max;
    wire [11:0] o_y_max;

    reg         got_bbox;
    reg [11:0]  cap_x_min;
    reg [11:0]  cap_y_min;
    reg [11:0]  cap_x_max;
    reg [11:0]  cap_y_max;

    plate_accel_top #(
        .IMG_W(IMG_W),
        .IMG_H(IMG_H),
        .TH_LOW(8'd80),
        .TH_HIGH(8'd230),
        .MIN_W(4),
        .MIN_H(3)
    ) dut (
        .clk(clk),
        .rst_n(rst_n),
        .i_valid(i_valid),
        .i_sof(i_sof),
        .i_eol(i_eol),
        .i_eof(i_eof),
        .i_r(i_r),
        .i_g(i_g),
        .i_b(i_b),
        .o_valid(o_valid),
        .o_sof(o_sof),
        .o_eol(o_eol),
        .o_eof(o_eof),
        .o_gray(o_gray),
        .o_bin(o_bin),
        .o_bbox_valid(o_bbox_valid),
        .o_x_min(o_x_min),
        .o_y_min(o_y_min),
        .o_x_max(o_x_max),
        .o_y_max(o_y_max)
    );

    always #5 clk = ~clk;

    always @(posedge clk) begin
        if (o_bbox_valid) begin
            got_bbox <= 1'b1;
            cap_x_min <= o_x_min;
            cap_y_min <= o_y_min;
            cap_x_max <= o_x_max;
            cap_y_max <= o_y_max;
        end
    end

    task send_frame;
        integer x;
        integer y;
        begin
            for (y = 0; y < IMG_H; y = y + 1) begin
                for (x = 0; x < IMG_W; x = x + 1) begin
                    @(posedge clk);
                    i_valid <= 1'b1;
                    i_sof   <= (x == 0 && y == 0);
                    i_eol   <= (x == IMG_W - 1);
                    i_eof   <= (x == IMG_W - 1 && y == IMG_H - 1);

                    if (x >= 4 && x <= 10 && y >= 3 && y <= 6) begin
                        i_r <= 8'd200;
                        i_g <= 8'd200;
                        i_b <= 8'd200;
                    end else begin
                        i_r <= 8'd20;
                        i_g <= 8'd20;
                        i_b <= 8'd20;
                    end
                end
            end

            @(posedge clk);
            i_valid <= 1'b0;
            i_sof   <= 1'b0;
            i_eol   <= 1'b0;
            i_eof   <= 1'b0;
            i_r     <= 8'd0;
            i_g     <= 8'd0;
            i_b     <= 8'd0;
        end
    endtask

    initial begin
        clk = 1'b0;
        rst_n = 1'b0;
        i_valid = 1'b0;
        i_sof = 1'b0;
        i_eol = 1'b0;
        i_eof = 1'b0;
        i_r = 8'd0;
        i_g = 8'd0;
        i_b = 8'd0;

        got_bbox = 1'b0;
        cap_x_min = 12'd0;
        cap_y_min = 12'd0;
        cap_x_max = 12'd0;
        cap_y_max = 12'd0;

        repeat (5) @(posedge clk);
        rst_n = 1'b1;

        send_frame();

        repeat (10) @(posedge clk);

        if (!got_bbox) begin
            $display("[FAIL] bbox_valid not asserted");
            $stop;
        end

        if (cap_x_min != 12'd4 || cap_y_min != 12'd3 || cap_x_max != 12'd10 || cap_y_max != 12'd6) begin
            $display("[FAIL] bbox mismatch: (%0d,%0d)-(%0d,%0d)", cap_x_min, cap_y_min, cap_x_max, cap_y_max);
            $stop;
        end

        $display("[PASS] bbox matched expected ROI");
        $finish;
    end

endmodule
