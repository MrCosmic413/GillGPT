module kevin_motor_controller (
    input clk,
    input uart_rx,

    output reg uart_tx,

    // Mouth / Motor A
    output reg ain1,
    output reg ain2,
    output pwma,

    // Head + Tail / Motor B
    output reg bin1,
    output reg bin2,
    output pwmb,

    // TB6612 enable
    output reg stby
);

    // =====================================================
    // CLOCK / UART SETTINGS
    // =====================================================

    parameter CLKS_PER_BIT = 234;

    // 27 MHz / 27000 = 1 kHz PWM
    parameter PWM_PERIOD = 27000;


    // =====================================================
    // KEVIN CALIBRATION
    // =====================================================



    // -----------------------------------------------------
    // MOUTH TIMINGS
    // -----------------------------------------------------

    // Quiet speech
    localparam MOUTH_QUIET_OPEN  = 1620000; // 0.060 s
    localparam MOUTH_QUIET_CLOSE = 2025000; // 0.075 s

    // Normal short
    localparam MOUTH_NORMAL_SHORT_OPEN  = 2160000; // 0.080 s
    localparam MOUTH_NORMAL_SHORT_CLOSE = 1755000; // 0.065 s

    // Normal long
    localparam MOUTH_NORMAL_LONG_OPEN  = 3375000; // 0.125 s
    localparam MOUTH_NORMAL_LONG_CLOSE = 2160000; // 0.080 s

    // Emphasis fast
    localparam MOUTH_EMPH_FAST_OPEN  = 2565000; // 0.095 s
    localparam MOUTH_EMPH_FAST_CLOSE = 1485000; // 0.055 s

    // Emphasis long
    localparam MOUTH_EMPH_LONG_OPEN  = 3645000; // 0.135 s
    localparam MOUTH_EMPH_LONG_CLOSE = 2025000; // 0.075 s

    localparam MOUTH_PWM = 21600;            // 80%
    localparam BODY_PWM = 20250;             // 75%
    localparam HEAD_HOME_MAIN_PWM = 20250;   // 75%
    localparam HEAD_HOME_FINAL_PWM = 12150;  // 45%


    // -----------------------------------------------------
    // HEAD TIMINGS
    // -----------------------------------------------------

    localparam HEAD_OUT_TIME =
        18900000; // 0.70 s

    localparam HEAD_HOME_MAIN_TIME =
        12420000; // 0.46 s

    localparam HEAD_HOME_SETTLE_TIME =
        2700000; // 0.10 s

    localparam HEAD_HOME_FINAL_TIME =
        1080000; // 0.04 s


    // -----------------------------------------------------
    // TAIL TIMINGS
    // -----------------------------------------------------

    localparam TAIL_OUT_TIME =
        14850000; // 0.55 s

    localparam TAIL_SPRING_WAIT =
        4050000; // 0.15 s

    localparam TAIL_RESET_TIME =
        8100000; // 0.30 s


    // =====================================================
    // UART RX STATES
    // =====================================================

    localparam RX_IDLE  = 3'd0;
    localparam RX_START = 3'd1;
    localparam RX_DATA  = 3'd2;
    localparam RX_STOP  = 3'd3;


    // =====================================================
    // UART TX STATES
    // =====================================================

    localparam TX_IDLE  = 3'd0;
    localparam TX_START = 3'd1;
    localparam TX_DATA  = 3'd2;
    localparam TX_STOP  = 3'd3;


    // =====================================================
    // MOUTH STATES
    // =====================================================

    localparam MOUTH_IDLE  = 2'd0;
    localparam MOUTH_OPEN  = 2'd1;
    localparam MOUTH_CLOSE = 2'd2;


    // =====================================================
    // BODY STATES
    // =====================================================

    localparam BODY_HOME =
        4'd0;

    localparam BODY_HEAD_OUT_MOVING =
        4'd1;

    localparam BODY_HEAD_OUT =
        4'd2;

    localparam BODY_HEAD_HOME_MAIN =
        4'd3;

    localparam BODY_HEAD_HOME_SETTLE =
        4'd4;

    localparam BODY_HEAD_HOME_FINAL =
        4'd5;

    localparam BODY_TAIL_OUT =
        4'd6;

    localparam BODY_TAIL_WAIT =
        4'd7;

    localparam BODY_TAIL_RESET =
        4'd8;


    // =====================================================
    // UART RX REGISTERS
    // =====================================================

    reg [2:0] rx_state = RX_IDLE;

    reg [8:0] rx_clock_count = 0;
    reg [2:0] rx_bit_index = 0;

    reg [7:0] received_byte = 0;

    reg rx_meta = 1'b1;
    reg rx_sync = 1'b1;

    // One-clock pulse saying:
    // "A command has arrived."
    reg command_valid = 1'b0;

    reg [7:0] command_byte = 0;


    // =====================================================
    // UART TX REGISTERS
    // =====================================================

    reg [2:0] tx_state = TX_IDLE;

    reg [8:0] tx_clock_count = 0;
    reg [2:0] tx_bit_index = 0;

    reg [7:0] tx_byte = 0;

    reg response_valid = 1'b0;
    reg [7:0] response_byte = 0;


    // =====================================================
    // PWM REGISTERS
    // =====================================================

    reg [15:0] pwm_counter = 0;

    reg [15:0] mouth_pwm_duty = 0;
    reg [15:0] body_pwm_duty = 0;

    reg mouth_pwm_enable = 1'b0;
    reg body_pwm_enable = 1'b0;


    assign pwma =
        mouth_pwm_enable &&
        (pwm_counter < mouth_pwm_duty);

    assign pwmb =
        body_pwm_enable &&
        (pwm_counter < body_pwm_duty);


    always @(posedge clk) begin

        if (pwm_counter >= PWM_PERIOD - 1)
            pwm_counter <= 0;

        else
            pwm_counter <= pwm_counter + 1'b1;

    end


    // =====================================================
    // UART INPUT SYNCHRONIZER
    // =====================================================

    always @(posedge clk) begin

        rx_meta <= uart_rx;
        rx_sync <= rx_meta;

    end


    // =====================================================
    // UART RECEIVER
    // =====================================================

    always @(posedge clk) begin

        command_valid <= 1'b0;


        case (rx_state)

            // -------------------------------------------------
            // IDLE
            // -------------------------------------------------

            RX_IDLE: begin

                rx_clock_count <= 0;
                rx_bit_index <= 0;

                if (rx_sync == 1'b0)
                    rx_state <= RX_START;

            end


            // -------------------------------------------------
            // START BIT
            // -------------------------------------------------

            RX_START: begin

                if (
                    rx_clock_count ==
                    CLKS_PER_BIT / 2
                ) begin

                    rx_clock_count <= 0;

                    if (rx_sync == 1'b0)
                        rx_state <= RX_DATA;

                    else
                        rx_state <= RX_IDLE;

                end

                else begin

                    rx_clock_count <=
                        rx_clock_count + 1'b1;

                end

            end


            // -------------------------------------------------
            // DATA BITS
            // -------------------------------------------------

            RX_DATA: begin

                if (
                    rx_clock_count ==
                    CLKS_PER_BIT - 1
                ) begin

                    rx_clock_count <= 0;

                    received_byte[
                        rx_bit_index
                    ] <= rx_sync;


                    if (rx_bit_index == 3'd7) begin

                        rx_bit_index <= 0;

                        rx_state <= RX_STOP;

                    end

                    else begin

                        rx_bit_index <=
                            rx_bit_index + 1'b1;

                    end

                end

                else begin

                    rx_clock_count <=
                        rx_clock_count + 1'b1;

                end

            end


            // -------------------------------------------------
            // STOP BIT
            // -------------------------------------------------

            RX_STOP: begin

                if (
                    rx_clock_count ==
                    CLKS_PER_BIT - 1
                ) begin

                    rx_clock_count <= 0;

                    command_byte <= received_byte;
                    command_valid <= 1'b1;

                    rx_state <= RX_IDLE;

                end

                else begin

                    rx_clock_count <=
                        rx_clock_count + 1'b1;

                end

            end


            default: begin

                rx_state <= RX_IDLE;

            end

        endcase

    end


    // =====================================================
    // MOUTH CONTROLLER
    // =====================================================

    reg [1:0] mouth_state = MOUTH_IDLE;

    reg [22:0] mouth_timer = 0;

    reg [22:0] mouth_open_time = 0;
    reg [22:0] mouth_close_time = 0;


    always @(posedge clk) begin

        case (mouth_state)

            // -------------------------------------------------
            // MOUTH IDLE
            // -------------------------------------------------

            MOUTH_IDLE: begin

                ain1 <= 1'b0;
                ain2 <= 1'b0;

                mouth_pwm_enable <= 1'b0;
                mouth_pwm_duty <= MOUTH_PWM;

                mouth_timer <= 0;


                if (command_valid) begin

                    // =========================================
                    // q = QUIET
                    // =========================================

                    if (command_byte == 8'h71) begin

                        mouth_open_time <=
                            MOUTH_QUIET_OPEN;

                        mouth_close_time <=
                            MOUTH_QUIET_CLOSE;

                        mouth_state <=
                            MOUTH_OPEN;

                    end


                    // =========================================
                    // n = NORMAL SHORT
                    // =========================================

                    else if (
                        command_byte == 8'h6E
                    ) begin

                        mouth_open_time <=
                            MOUTH_NORMAL_SHORT_OPEN;

                        mouth_close_time <=
                            MOUTH_NORMAL_SHORT_CLOSE;

                        mouth_state <=
                            MOUTH_OPEN;

                    end


                    // =========================================
                    // N = NORMAL LONG
                    // =========================================

                    else if (
                        command_byte == 8'h4E
                    ) begin

                        mouth_open_time <=
                            MOUTH_NORMAL_LONG_OPEN;

                        mouth_close_time <=
                            MOUTH_NORMAL_LONG_CLOSE;

                        mouth_state <=
                            MOUTH_OPEN;

                    end


                    // =========================================
                    // e = EMPHASIS FAST
                    // =========================================

                    else if (
                        command_byte == 8'h65
                    ) begin

                        mouth_open_time <=
                            MOUTH_EMPH_FAST_OPEN;

                        mouth_close_time <=
                            MOUTH_EMPH_FAST_CLOSE;

                        mouth_state <=
                            MOUTH_OPEN;

                    end


                    // =========================================
                    // E = EMPHASIS LONG
                    // =========================================

                    else if (
                        command_byte == 8'h45
                    ) begin

                        mouth_open_time <=
                            MOUTH_EMPH_LONG_OPEN;

                        mouth_close_time <=
                            MOUTH_EMPH_LONG_CLOSE;

                        mouth_state <=
                            MOUTH_OPEN;

                    end

                end

            end


            // -------------------------------------------------
            // MOUTH OPEN
            // -------------------------------------------------

            MOUTH_OPEN: begin

                // Matches current KevinOS:
                //
                // AIN1 = ON
                // AIN2 = OFF

                ain1 <= 1'b1;
                ain2 <= 1'b0;

                mouth_pwm_enable <= 1'b1;
                mouth_pwm_duty <= MOUTH_PWM;


                if (
                    mouth_timer >=
                    mouth_open_time - 1
                ) begin

                    mouth_timer <= 0;

                    mouth_state <=
                        MOUTH_CLOSE;

                end

                else begin

                    mouth_timer <=
                        mouth_timer + 1'b1;

                end

            end


            // -------------------------------------------------
            // MOUTH CLOSE
            // -------------------------------------------------

            MOUTH_CLOSE: begin

                // Matches current KevinOS:
                //
                // AIN1 = OFF
                // AIN2 = ON

                ain1 <= 1'b0;
                ain2 <= 1'b1;

                mouth_pwm_enable <= 1'b1;
                mouth_pwm_duty <= MOUTH_PWM;


                if (
                    mouth_timer >=
                    mouth_close_time - 1
                ) begin

                    mouth_timer <= 0;

                    mouth_state <=
                        MOUTH_IDLE;

                end

                else begin

                    mouth_timer <=
                        mouth_timer + 1'b1;

                end

            end


            default: begin

                mouth_state <= MOUTH_IDLE;

            end

        endcase


        // Emergency stop always wins.

        if (
            command_valid &&
            command_byte == 8'h53
        ) begin

            mouth_state <= MOUTH_IDLE;

            ain1 <= 1'b0;
            ain2 <= 1'b0;

            mouth_pwm_enable <= 1'b0;

            mouth_timer <= 0;

        end

    end


    // =====================================================
    // BODY CONTROLLER
    // =====================================================

    reg [3:0] body_state = BODY_HOME;

    reg [24:0] body_timer = 0;


    always @(posedge clk) begin

        case (body_state)

            // -------------------------------------------------
            // HOME
            // -------------------------------------------------

            BODY_HOME: begin

                bin1 <= 1'b0;
                bin2 <= 1'b0;

                body_pwm_enable <= 1'b0;
                body_pwm_duty <= BODY_PWM;

                body_timer <= 0;


                if (command_valid) begin

                    // =========================================
                    // H = HEAD OUT
                    // =========================================

                    if (
                        command_byte == 8'h48
                    ) begin

                        body_state <=
                            BODY_HEAD_OUT_MOVING;

                    end


                    // =========================================
                    // T = TAIL WAG
                    // =========================================

                    else if (
                        command_byte == 8'h54
                    ) begin

                        body_state <=
                            BODY_TAIL_OUT;

                    end

                end

            end


            // -------------------------------------------------
            // HEAD MOVING OUT
            // -------------------------------------------------

            BODY_HEAD_OUT_MOVING: begin

                // Electrical IN
                //
                // BIN1 = OFF
                // BIN2 = ON

                bin1 <= 1'b0;
                bin2 <= 1'b1;

                body_pwm_enable <= 1'b1;
                body_pwm_duty <= BODY_PWM;


                if (
                    body_timer >=
                    HEAD_OUT_TIME - 1
                ) begin

                    body_timer <= 0;

                    body_state <=
                        BODY_HEAD_OUT;

                end

                else begin

                    body_timer <=
                        body_timer + 1'b1;

                end

            end


            // -------------------------------------------------
            // HEAD IS OUT
            // -------------------------------------------------

            BODY_HEAD_OUT: begin

                bin1 <= 1'b0;
                bin2 <= 1'b0;

                body_pwm_enable <= 1'b0;

                body_timer <= 0;


                if (
                    command_valid &&
                    command_byte == 8'h68
                ) begin

                    body_state <=
                        BODY_HEAD_HOME_MAIN;

                end

                // TAIL COMMAND IS IGNORED HERE.
                //
                // This is one of our FPGA
                // safety rules.

            end


            // -------------------------------------------------
            // HEAD HOME - MAIN RETURN
            // -------------------------------------------------

            BODY_HEAD_HOME_MAIN: begin

                // Electrical OUT

                bin1 <= 1'b1;
                bin2 <= 1'b0;

                body_pwm_enable <= 1'b1;

                body_pwm_duty <=
                    HEAD_HOME_MAIN_PWM;


                if (
                    body_timer >=
                    HEAD_HOME_MAIN_TIME - 1
                ) begin

                    body_timer <= 0;

                    body_state <=
                        BODY_HEAD_HOME_SETTLE;

                end

                else begin

                    body_timer <=
                        body_timer + 1'b1;

                end

            end


            // -------------------------------------------------
            // HEAD HOME - SETTLE
            // -------------------------------------------------

            BODY_HEAD_HOME_SETTLE: begin

                bin1 <= 1'b0;
                bin2 <= 1'b0;

                body_pwm_enable <= 1'b0;

                if (
                    body_timer >=
                    HEAD_HOME_SETTLE_TIME - 1
                ) begin

                    body_timer <= 0;

                    body_state <=
                        BODY_HEAD_HOME_FINAL;

                end

                else begin

                    body_timer <=
                        body_timer + 1'b1;

                end

            end


            // -------------------------------------------------
            // HEAD HOME - FINAL BUMP
            // -------------------------------------------------

            BODY_HEAD_HOME_FINAL: begin

                bin1 <= 1'b1;
                bin2 <= 1'b0;

                body_pwm_enable <= 1'b1;

                body_pwm_duty <=
                    HEAD_HOME_FINAL_PWM;


                if (
                    body_timer >=
                    HEAD_HOME_FINAL_TIME - 1
                ) begin

                    body_timer <= 0;

                    body_state <=
                        BODY_HOME;

                end

                else begin

                    body_timer <=
                        body_timer + 1'b1;

                end

            end


            // -------------------------------------------------
            // TAIL OUT
            // -------------------------------------------------

            BODY_TAIL_OUT: begin

                // Electrical OUT

                bin1 <= 1'b1;
                bin2 <= 1'b0;

                body_pwm_enable <= 1'b1;
                body_pwm_duty <= BODY_PWM;


                if (
                    body_timer >=
                    TAIL_OUT_TIME - 1
                ) begin

                    body_timer <= 0;

                    body_state <=
                        BODY_TAIL_WAIT;

                end

                else begin

                    body_timer <=
                        body_timer + 1'b1;

                end

            end


            // -------------------------------------------------
            // TAIL SPRING RETURN WAIT
            // -------------------------------------------------

            BODY_TAIL_WAIT: begin

                bin1 <= 1'b0;
                bin2 <= 1'b0;

                body_pwm_enable <= 1'b0;


                if (
                    body_timer >=
                    TAIL_SPRING_WAIT - 1
                ) begin

                    body_timer <= 0;

                    body_state <=
                        BODY_TAIL_RESET;

                end

                else begin

                    body_timer <=
                        body_timer + 1'b1;

                end

            end


            // -------------------------------------------------
            // TAIL RESET
            // -------------------------------------------------

            BODY_TAIL_RESET: begin

                // Electrical IN

                bin1 <= 1'b0;
                bin2 <= 1'b1;

                body_pwm_enable <= 1'b1;
                body_pwm_duty <= BODY_PWM;


                if (
                    body_timer >=
                    TAIL_RESET_TIME - 1
                ) begin

                    body_timer <= 0;

                    body_state <=
                        BODY_HOME;

                end

                else begin

                    body_timer <=
                        body_timer + 1'b1;

                end

            end


            default: begin

                body_state <= BODY_HOME;

            end

        endcase


        // Emergency STOP

        if (
            command_valid &&
            command_byte == 8'h53
        ) begin

            body_state <= BODY_HOME;

            bin1 <= 1'b0;
            bin2 <= 1'b0;

            body_pwm_enable <= 1'b0;

            body_timer <= 0;

        end

    end


    // =====================================================
    // RESPONSE GENERATOR
    // =====================================================

    // This block generates one UART acknowledgement
    // for every recognized command.

    always @(posedge clk) begin

        response_valid <= 1'b0;

        if (command_valid) begin

            // Mouth commands
            if (
                command_byte == 8'h71 ||
                command_byte == 8'h6E ||
                command_byte == 8'h4E ||
                command_byte == 8'h65 ||
                command_byte == 8'h45
            ) begin

                // M = mouth command accepted
                response_byte <= 8'h4D;
                response_valid <= 1'b1;

            end


            // Head out
            else if (
                command_byte == 8'h48
            ) begin

                // H
                response_byte <= 8'h48;
                response_valid <= 1'b1;

            end


            // Head home
            else if (
                command_byte == 8'h68
            ) begin

                // h
                response_byte <= 8'h68;
                response_valid <= 1'b1;

            end


            // Tail
            else if (
                command_byte == 8'h54
            ) begin

                // T
                response_byte <= 8'h54;
                response_valid <= 1'b1;

            end


            // Stop
            else if (
                command_byte == 8'h53
            ) begin

                // S
                response_byte <= 8'h53;
                response_valid <= 1'b1;

            end

        end

    end


    // =====================================================
    // UART TRANSMITTER
    // =====================================================

    always @(posedge clk) begin

        case (tx_state)

            TX_IDLE: begin

                uart_tx <= 1'b1;

                tx_clock_count <= 0;
                tx_bit_index <= 0;


                if (response_valid) begin

                    tx_byte <= response_byte;

                    tx_state <= TX_START;

                end

            end


            TX_START: begin

                uart_tx <= 1'b0;


                if (
                    tx_clock_count ==
                    CLKS_PER_BIT - 1
                ) begin

                    tx_clock_count <= 0;

                    tx_state <= TX_DATA;

                end

                else begin

                    tx_clock_count <=
                        tx_clock_count + 1'b1;

                end

            end


            TX_DATA: begin

                uart_tx <=
                    tx_byte[tx_bit_index];


                if (
                    tx_clock_count ==
                    CLKS_PER_BIT - 1
                ) begin

                    tx_clock_count <= 0;


                    if (
                        tx_bit_index == 3'd7
                    ) begin

                        tx_bit_index <= 0;

                        tx_state <= TX_STOP;

                    end

                    else begin

                        tx_bit_index <=
                            tx_bit_index + 1'b1;

                    end

                end

                else begin

                    tx_clock_count <=
                        tx_clock_count + 1'b1;

                end

            end


            TX_STOP: begin

                uart_tx <= 1'b1;


                if (
                    tx_clock_count ==
                    CLKS_PER_BIT - 1
                ) begin

                    tx_clock_count <= 0;

                    tx_state <= TX_IDLE;

                end

                else begin

                    tx_clock_count <=
                        tx_clock_count + 1'b1;

                end

            end


            default: begin

                tx_state <= TX_IDLE;

            end

        endcase

    end


    // =====================================================
    // SAFE INITIAL STATE
    // =====================================================

    initial begin

        uart_tx = 1'b1;

        ain1 = 1'b0;
        ain2 = 1'b0;

        bin1 = 1'b0;
        bin2 = 1'b0;

        stby = 1'b1;

    end


endmodule