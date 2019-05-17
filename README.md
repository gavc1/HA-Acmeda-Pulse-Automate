# HA-Acmeda-Pulse-Automate
Prototype component for connecting Acmeda Covers connected to a Pulse hub via serial

The hub can be connected over RS485, see this document for more info
https://www.rolleaseacmeda.com/docs/default-source/us/smart-home-integration/serial-protocol/serialguide_installscenarios.pdf?sfvrsn=22

Configure each motor with a hub id, motor id, and serial port, in your configuration.yaml eg 
cover:
  - platform: PulseCover
    port: "/dev/ttyS0"
    covers:
      SlidingDoor:
        friendly_name: "Sliding Door Blinds"
        hub_id: "187"
        motor_id: "001"
        port: "/dev/ttyS0"
