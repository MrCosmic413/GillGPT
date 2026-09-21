module kevin_nano_motor (
    input clk,
    input uart_rx,
    output reg uart_tx,

    output reg ain1,
    output reg ain2,
    output pwma,
    output reg stby
);

    // =====================================================
    // CLOCK / UART
    // =====================================================

    parameter CLKS_PER_BIT = 234;

    // 1 kHz PWM
    // 27 MHz / 27000 = 1000 Hz
    parameter PWM_PERIOD = 27000;

    // 40% duty cycle
    parameter PWM_DUTY = 10800;

    // About 70 ms at 27 MHz
    parameter MOTOR_TIME = 1890000;


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
    // MOTOR STATES
    // =====================================================

    localparam MOTOR_IDLE  = 2'd0;
    localparam MOTOR_OPEN  = 2'd1;
    localparam MOTOR_CLOSE = 2'd2;


    // =====================================================
    // UART RX REGISTERS
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
    // UART TX REGISTERS
    // =====================================================

    reg [2:0] tx_state = TX_IDLE;

    reg [8:0] tx_clock_count = 0;
    reg [2:0] tx_bit_index = 0;

    reg [7:0] tx_byte = 0;


    // =====================================================
    // COMMAND PULSES
    // =====================================================

    reg command_open  = 1'b0;
    reg command_close = 1'b0;
    reg command_stop  = 1'b0;


    // =====================================================
    // PWM
    // =====================================================

    reg [15:0] pwm_counter = 0;

    reg pwm_enable = 1'b0;

    assign pwma =
        pwm_enable &&
        (pwm_counter < PWM_DUTY);


    always @(posedge clk) begin

        if (pwm_counter >= PWM_PERIOD - 1)
            pwm_counter <= 0;
        else
            pwm_counter <= pwm_counter + 1'b1;

    end


    // =====================================================
    // MOTOR CONTROL
    // =====================================================

    reg [1:0] motor_state = MOTOR_IDLE;

    reg [20:0] motor_timer = 0;


    always @(posedge clk) begin

        // ---------------------------------------------
        // Immediate STOP command
        // ---------------------------------------------

        if (command_stop) begin

            motor_state <= MOTOR_IDLE;

            ain1 <= 1'b0;
            ain2 <= 1'b0;

            pwm_enable <= 1'b0;

            motor_timer <= 0;

        end

        else begin

            case (motor_state)

                // =========================================
                // IDLE
                // =========================================

                MOTOR_IDLE: begin

                    ain1 <= 1'b0;
                    ain2 <= 1'b0;

                    pwm_enable <= 1'b0;

                    motor_timer <= 0;

                    if (command_open) begin

                        motor_state <= MOTOR_OPEN;

                    end

                    else if (command_close) begin

                        motor_state <= MOTOR_CLOSE;

                    end

                end


                // =========================================
                // OPEN
                // =========================================

                MOTOR_OPEN: begin

                    ain1 <= 1'b0;
                    ain2 <= 1'b1;

                    pwm_enable <= 1'b1;

                    if (
                        motor_timer >= MOTOR_TIME - 1
                    ) begin

                        motor_timer <= 0;

                        motor_state <= MOTOR_IDLE;

                    end

                    else begin

                        motor_timer <=
                            motor_timer + 1'b1;

                    end

                end


                // =========================================
                // CLOSE
                // =========================================

                MOTOR_CLOSE: begin

                    ain1 <= 1'b1;
                    ain2 <= 1'b0;

                    pwm_enable <= 1'b1;

                    if (
                        motor_timer >= MOTOR_TIME - 1
                    ) begin

                        motor_timer <= 0;

                        motor_state <= MOTOR_IDLE;

                    end

                    else begin

                        motor_timer <=
                            motor_timer + 1'b1;

                    end

                end


                // =========================================
                // DEFAULT
                // =========================================

                default: begin

                    motor_state <= MOTOR_IDLE;

                end

            endcase

        end

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

        // These pulses are normally LOW.
        // They go HIGH for exactly one clock cycle
        // when the matching command arrives.

        command_open  <= 1'b0;
        command_close <= 1'b0;
        command_stop  <= 1'b0;

        rx_valid <= 1'b0;


        case (rx_state)

            // =========================================
            // IDLE
            // =========================================

            RX_IDLE: begin

                rx_clock_count <= 0;
                rx_bit_index <= 0;

                if (rx_sync == 1'b0)
                    rx_state <= RX_START;

            end


            // =========================================
            // START BIT
            // =========================================

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


            // =========================================
            // DATA BITS
            // =========================================

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


            // =========================================
            // STOP BIT + COMMAND HANDLING
            // =========================================

            RX_STOP: begin

                if (
                    rx_clock_count ==
                    CLKS_PER_BIT - 1
                ) begin

                    rx_clock_count <= 0;


                    // ---------------------------------
                    // ASCII O = OPEN
                    // ---------------------------------

                    if (
                        received_byte == 8'h4F
                    ) begin

                        command_open <= 1'b1;

                        response_byte <= 8'h41;

                        rx_valid <= 1'b1;

                    end


                    // ---------------------------------
                    // ASCII C = CLOSE
                    // ---------------------------------

                    else if (
                        received_byte == 8'h43
                    ) begin

                        command_close <= 1'b1;

                        response_byte <= 8'h42;

                        rx_valid <= 1'b1;

                    end


                    // ---------------------------------
                    // ASCII S = STOP
                    // ---------------------------------

                    else if (
                        received_byte == 8'h53
                    ) begin

                        command_stop <= 1'b1;

                        response_byte <= 8'h53;

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
    // INITIAL OUTPUT STATES
    // =====================================================

    initial begin

        uart_tx = 1'b1;

        ain1 = 1'b0;
        ain2 = 1'b0;

        stby = 1'b1;

    end


    // =====================================================
    // UART TRANSMITTER
    // =====================================================

    always @(posedge clk) begin

        case (tx_state)

            // =========================================
            // IDLE
            // =========================================

            TX_IDLE: begin

                uart_tx <= 1'b1;

                tx_clock_count <= 0;
                tx_bit_index <= 0;

                if (rx_valid) begin

                    tx_byte <= response_byte;

                    tx_state <= TX_START;

                end

            end


            // =========================================
            // START BIT
            // =========================================

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


            // =========================================
            // DATA BITS
            // =========================================

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


            // =========================================
            // STOP BIT
            // =========================================

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