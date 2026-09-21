module kevin_nano_uart (
    input  clk,
    input  uart_rx,
    output reg uart_tx,
    output reg led
);

    // =====================================================
    // CLOCK / UART SETTINGS
    // =====================================================

    // Tang Nano 9K onboard clock = 27 MHz
    // UART baud rate = 115200
    //
    // 27,000,000 / 115,200 ≈ 234
    //
    parameter CLKS_PER_BIT = 234;


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
    // RX REGISTERS
    // =====================================================

    reg [2:0] rx_state = RX_IDLE;

    reg [8:0] rx_clock_count = 0;
    reg [2:0] rx_bit_index = 0;

    reg [7:0] received_byte = 0;

    // Synchronize asynchronous UART input
    reg rx_meta = 1'b1;
    reg rx_sync = 1'b1;


    // =====================================================
    // TX REGISTERS
    // =====================================================

    reg [2:0] tx_state = TX_IDLE;

    reg [8:0] tx_clock_count = 0;
    reg [2:0] tx_bit_index = 0;

    reg [7:0] tx_byte = 0;

    reg tx_start_request = 1'b0;


    // =====================================================
    // INITIAL OUTPUT STATES
    // =====================================================

    initial begin

        // Tang Nano LEDs are active-low
        // 1 = OFF
        // 0 = ON

        led = 1'b1;

        // UART idle state is HIGH

        uart_tx = 1'b1;

    end


    // =====================================================
    // UART RX INPUT SYNCHRONIZER
    // =====================================================

    always @(posedge clk) begin

        rx_meta <= uart_rx;
        rx_sync <= rx_meta;

    end


    // =====================================================
    // UART RECEIVER
    // =====================================================

    always @(posedge clk) begin

        case (rx_state)


            // -------------------------------------------------
            // WAIT FOR START BIT
            // -------------------------------------------------

            RX_IDLE: begin

                rx_clock_count <= 0;
                rx_bit_index <= 0;

                if (rx_sync == 1'b0) begin

                    rx_state <= RX_START;

                end

            end


            // -------------------------------------------------
            // VERIFY START BIT
            // -------------------------------------------------

            RX_START: begin

                if (
                    rx_clock_count ==
                    (CLKS_PER_BIT / 2)
                ) begin

                    rx_clock_count <= 0;

                    if (rx_sync == 1'b0) begin

                        rx_state <= RX_DATA;

                    end
                    else begin

                        rx_state <= RX_IDLE;

                    end

                end
                else begin

                    rx_clock_count <=
                        rx_clock_count + 1'b1;

                end

            end


            // -------------------------------------------------
            // RECEIVE 8 DATA BITS
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
            // STOP BIT + COMMAND HANDLING
            // -------------------------------------------------

            RX_STOP: begin

                if (
                    rx_clock_count ==
                    CLKS_PER_BIT - 1
                ) begin

                    rx_clock_count <= 0;

                    // ASCII "1"
                    if (
                        received_byte == 8'h31
                    ) begin

                        // LED ON
                        led <= 1'b0;

                        // Send ASCII "A"
                        tx_byte <= 8'h41;

                        tx_start_request <= 1'b1;

                    end


                    // ASCII "0"
                    else if (
                        received_byte == 8'h30
                    ) begin

                        // LED OFF
                        led <= 1'b1;

                        // Send ASCII "B"
                        tx_byte <= 8'h42;

                        tx_start_request <= 1'b1;

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
            // WAIT FOR TRANSMIT REQUEST
            // -------------------------------------------------

            TX_IDLE: begin

                uart_tx <= 1'b1;

                tx_clock_count <= 0;
                tx_bit_index <= 0;

                if (tx_start_request) begin

                    // Clear request
                    tx_start_request <= 1'b0;

                    tx_state <= TX_START;

                end

            end


            // -------------------------------------------------
            // SEND START BIT
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
            // SEND 8 DATA BITS
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
            // SEND STOP BIT
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