# Independent constraints. NEVER load together with the old pins.xdc.
set_property PACKAGE_PIN W19 [get_ports clk_50m]
set_property IOSTANDARD LVCMOS33 [get_ports clk_50m]
create_clock -period 20.000 -name sys_clk [get_ports clk_50m]
set_property PACKAGE_PIN Y22 [get_ports uart_txd]
set_property IOSTANDARD LVCMOS33 [get_ports uart_txd]
set_property PACKAGE_PIN AA21 [get_ports {led[0]}]
set_property PACKAGE_PIN AA20 [get_ports {led[1]}]
set_property PACKAGE_PIN W22 [get_ports {led[2]}]
set_property PACKAGE_PIN W21 [get_ports {led[3]}]
set_property PACKAGE_PIN T20 [get_ports {led[4]}]
set_property PACKAGE_PIN R19 [get_ports {led[5]}]
set_property PACKAGE_PIN P19 [get_ports {led[6]}]
set_property PACKAGE_PIN U21 [get_ports {led[7]}]
set_property IOSTANDARD LVCMOS33 [get_ports {led[*]}]
# VAUX fixed analog function. NO digital IOSTANDARD/PULLUP/IBUF on these.
# Board PDF page 12: JD1 logical pin 6 -> R81 100ohm -> J5 AD15P.
# Board PDF page 12: JD1 logical pin 8 -> R91 100ohm -> H5 AD15N.
set_property PACKAGE_PIN J5 [get_ports vauxp15]
set_property PACKAGE_PIN H5 [get_ports vauxn15]
# Outputs are asynchronous human indicators/UART, not synchronous external buses.
set_false_path -to [get_ports {uart_txd led[*]}]
# CFGBVS / CONFIG_VOLTAGE intentionally unset: actual Bank0 wiring not confirmed.
# Do not downgrade DRC or invent values to generate a bitstream.
