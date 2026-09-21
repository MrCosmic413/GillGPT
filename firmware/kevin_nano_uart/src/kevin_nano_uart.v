module kevin_nano_uart (
    input clk,
    input uart_rx,
    output reg uart_tx,
    output led
);

    // =====================================================
    // CLOCK / UART
    // =====================================================

    parameter CLKS_PER_BIT = 234;

    // 27 MHz / 27000 = 1000 Hz PWM
    parameter PWM_PERIOD = 27000;


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
    // UART RX
    // =====================================================

    reg [2:0] rx_state = RX_IDLE;

    reg [8:0] rx_clock_count = 0;
    reg [2:0] rx_bit_index = 0;

    reg [7:0] received_byte = 0;

    reg rx_meta = 1'b1;
    reg rx_sync = 1'b1;

    reg rx_valid = 1'b0;
    reg [7:0] response_byte = 0;


    // =====================================================
    // UART TX
    // =====================================================

    reg [2:0] tx_state = TX_IDLE;

    reg [8:0] tx_clock_count = 0;
    reg [2:0] tx_bit_index = 0;

    reg [7:0] tx_byte = 0;


    // =====================================================
    // PWM
    // =====================================================

    reg [15:0] pwm_counter = 0;

    // Range:
    // 0 → 27000

    reg [15:0] pwm_duty = 0;

    wire pwm_signal;


    // =====================================================
    // UART INPUT SYNCHRONIZER
    // =====================================================

    always @(posedge clk) begin

        rx_meta <= uart_rx;
        rx_sync <= rx_meta;

    end


    // =====================================================
    // PWM COUNTER
    // =====================================================

    always @(posedge clk) begin

        if (pwm_counter >= PWM_PERIOD - 1)
            pwm_counter <= 0;
        else
            pwm_counter <= pwm_counter + 1'b1;

    end


    // PWM is high while counter is below duty level

    assign pwm_signal =
        (pwm_counter < pwm_duty);


    // Tang Nano onboard LED is ACTIVE LOW.
    //
    // PWM HIGH means we want LED ON,
    // therefore invert it.

    assign led = ~pwm_signal;


    // =====================================================
    // UART RECEIVER
    // =====================================================

    always @(posedge clk) begin

        rx_valid <= 1'b0;


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
            // DATA
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


                    if (
                        rx_bit_index == 3'd7
                    ) begin

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
            // STOP BIT + COMMAND PROCESSING
            // -------------------------------------------------

            RX_STOP: begin

                if (
                    rx_clock_count ==
                    CLKS_PER_BIT - 1
                ) begin

                    rx_clock_count <= 0;


                    // =========================================
                    // "0" = 0%
                    // =========================================

                    if (received_byte == 8'h30) begin

                        pwm_duty <= 0;

                        response_byte <= 8'h41;

                        rx_valid <= 1'b1;

                    end


                    // =========================================
                    // "1" = 25%
                    // =========================================

                    else if (received_byte == 8'h31) begin

                        pwm_duty <= 6750;

                        response_byte <= 8'h42;

                        rx_valid <= 1'b1;

                    end


                    // =========================================
                    // "2" = 50%
                    // =========================================

                    else if (received_byte == 8'h32) begin

                        pwm_duty <= 13500;

                        response_byte <= 8'h43;

                        rx_valid <= 1'b1;

                    end


                    // =========================================
                    // "3" = 75%
                    // =========================================

                    else if (received_byte == 8'h33) begin

                        pwm_duty <= 20250;

                        response_byte <= 8'h44;

                        rx_valid <= 1'b1;

                    end


                    // =========================================
                    // "4" = 100%
                    // =========================================

                    else if (received_byte == 8'h34) begin

                        pwm_duty <= PWM_PERIOD;

                        response_byte <= 8'h45;

                        rx_valid <= 1'b1;

                    end


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
    // UART TRANSMITTER
    // =====================================================

    always @(posedge clk) begin

        case (tx_state)


            // -------------------------------------------------
            // IDLE
            // -------------------------------------------------

            TX_IDLE: begin

                uart_tx <= 1'b1;

                tx_clock_count <= 0;
                tx_bit_index <= 0;


                if (rx_valid) begin

                    tx_byte <= response_byte;

                    tx_state <= TX_START;

                end

            end


            // -------------------------------------------------
            // START BIT
            // -------------------------------------------------

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


            // -------------------------------------------------
            // DATA
            // -------------------------------------------------

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


            // -------------------------------------------------
            // STOP BIT
            // -------------------------------------------------

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


endmodule