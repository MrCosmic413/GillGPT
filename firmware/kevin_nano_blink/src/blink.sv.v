module blink (
    input  logic clk,
    output logic led
);

    logic [24:0] counter = 0;

    always_ff @(posedge clk) begin
        counter <= counter + 1'b1;
    end

    assign led = ~counter[24];

endmodule