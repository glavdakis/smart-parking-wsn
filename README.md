# Smart Parking with a Wireless Sensor Network

This repository contains the project for the **Applications of Telecommunication Devices** course at ECE AUTH during the 2024–2025 academic year.

| Folder | Contents |
|---|---|
| `firmware` | Arduino sketches for the sensor node (`transmitter`) and the base station (`receiver`) |
| `gui` | Python/Tkinter app that monitors the parking areas |
| `libraries` | Arduino libraries used: RF22 and Ultrasonic |
| `docs` | Report, presentation and photos of the setup |

## Sensor Network
Each parking lot has a sensor node: an Arduino with an RFM22 radio and two ultrasonic sensors, one at the entrance and one at the exit. Every 0.5 s the node measures the distances, and when an object comes closer than 10 cm it sends an `ENTER` or `EXIT` message. A second Arduino acts as the base station: it receives the messages, acknowledges them and forwards them to the computer over the serial port. The link uses the RF22Router library at 433 MHz with OOK modulation at 40 kbps and 20 dBm.

## Monitoring App
The app shows five parking areas of 50 spots each on a map of Los Angeles. When the user selects an area, the messages from the serial port update its occupied and available spots. The app also shows the area's pricing, an occupancy bar that turns from blue to orange to red, a warning when the lot is full, and an activity log. Manual controls simulate cars entering and leaving without the hardware.

## Capacity Analysis
Each event is a message of at most 100 bits, sent about once per second, so a transmission at 100 kbps lasts about 1 ms. Treating the nodes as a pure ALOHA network, the channel throughput of $S_{max} = 0.186$ supports about 186 parking lots sharing one channel.
