module uart_led (
    input clk,
    input uart_rx,
    output reg led
);

    // Tang Nano clock = 27 MHz
    // UART baud = 115200
    //
    // 27,000,000 / 115,200 = 234.375
    //
    // We use 234 clock cycles per UART bit.

    parameter CLKS_PER_BIT = 234;

    // UART receiver states
    localparam IDLE  = 3'd0;
    localparam START = 3'd1;
    localparam DATA  = 3'd2;
    localparam STOP  = 3'd3;

    reg [2:0] state = IDLE;

    reg [8:0] clock_count = 0;
    reg [2:0] bit_index = 0;

    reg [7:0] received_byte = 0;

    // Synchronize the asynchronous UART input
    reg rx_meta = 1'b1;
    reg rx_sync = 1'b1;

    // Nano LEDs are active-low:
    //
    // led = 0 → ON
    // led = 1 → OFF

    initial begin
        led = 1'b1;
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

        case (state)

            // ---------------------------------------------
            // WAIT FOR START BIT
            // ---------------------------------------------

            IDLE: begin

                clock_count <= 0;
                bit_index <= 0;

                // UART idle is HIGH.
                // LOW means a start bit has begun.

                if (rx_sync == 1'b0) begin
                    state <= START;
                end

            end


            // ---------------------------------------------
            // VERIFY START BIT
            // ---------------------------------------------

            START: begin

                // Move to approximately the middle
                // of the start bit.

                if (clock_count == (CLKS_PER_BIT / 2)) begin

                    clock_count <= 0;

                    // Make sure the signal is
                    // still LOW.

                    if (rx_sync == 1'b0)
                        state <= DATA;
                    else
                        state <= IDLE;

                end
                else begin

                    clock_count <= clock_count + 1'b1;

                end

            end


            // ---------------------------------------------
            // READ 8 DATA BITS
            // ---------------------------------------------

            DATA: begin

                if (clock_count == CLKS_PER_BIT - 1) begin

                    clock_count <= 0;

                    received_byte[bit_index] <= rx_sync;

                    if (bit_index == 3'd7) begin

                        bit_index <= 0;

                        state <= STOP;

                    end
                    else begin

                        bit_index <= bit_index + 1'b1;

                    end

                end
                else begin

                    clock_count <= clock_count + 1'b1;

                end

            end


            // ---------------------------------------------
            // STOP BIT
            // ---------------------------------------------

            STOP: begin

                if (clock_count == CLKS_PER_BIT - 1) begin

                    clock_count <= 0;

                    // ASCII "1" = hexadecimal 31
                    // ASCII "0" = hexadecimal 30

                    if (received_byte == 8'h31) begin

                        // Turn LED ON
                        led <= 1'b0;

                    end
                    else if (received_byte == 8'h30) begin

                        // Turn LED OFF
                        led <= 1'b1;

                    end

                    state <= IDLE;

                end
                else begin

                    clock_count <= clock_count + 1'b1;

                end

            end


            default: begin

                state <= IDLE;

            end

        endcase

    end

endmodule