#include <SPI.h>
#include <RF22.h>
#include <RF22Router.h>
#include "Ultrasonic.h"

#define MY_ADDRESS 10 // define my unique address
#define DESTINATION_ADDRESS_1 20 // define who I can talk to

// Singleton instance of the radio
RF22Router rf22(MY_ADDRESS); // initiate the class to talk to my radio with MY_ADDRESS

// Define pins ultrasonic(trig,echo)
Ultrasonic ultrasonic_in(A0, A1);
Ultrasonic ultrasonic_out(A2, A3);

//Variables
int distance_in;
int distance_out; 
int counter=0;

// State tracking variables for passage detection
bool prev_object_in = false;   // Previous state of entrance sensor
bool prev_object_out = false;  // Previous state of exit sensor
bool curr_object_in = false;   // Current state of entrance sensor
bool curr_object_out = false;  // Current state of exit sensor

void setup() {
  Serial.begin(9600); // to be able to view the results in the computer's monitor
  if (!rf22.init()) // initialize my radio
    Serial.println("RF22 init failed");
  // Defaults after init are 434.0MHz, 0.05MHz AFC pull-in, modulation FSK_Rb2_4Fd36
  if (!rf22.setFrequency(433.0)) // set the desired frequency
    Serial.println("setFrequency Fail");
  rf22.setTxPower(RF22_TXPOW_20DBM); // set the desired power for my transmitter in dBm
  //1,2,5,8,11,14,17,20 DBM
  rf22.setModemConfig(RF22::OOK_Rb40Bw335); // set the desired modulation
  //modulation

  // Manually define the routes for this network
  rf22.addRouteTo(DESTINATION_ADDRESS_1, DESTINATION_ADDRESS_1); // tells my radio card that if I want to send data to DESTINATION_ADDRESS_1 then I will send them directly to DESTINATION_ADDRESS_1 and not to another radio who would act as a relay
  delay(500); // delay for 0.5 sec
}

void loop() {
  // Store previous states
  prev_object_in = curr_object_in;
  prev_object_out = curr_object_out;
  
  // Read current distances
  distance_in = ultrasonic_in.Ranging(CM); //Use 'CM' for centimeters or 'INC' for inches
  distance_out = ultrasonic_out.Ranging(CM); //Use 'CM' for centimeters or 'INC' for inches
  
  // Update current states
  curr_object_in = (distance_in < 10);
  curr_object_out = (distance_out < 10);
  
  //Print distance...
  Serial.print("Object found in entrance at: ");
  Serial.print(distance_in);
  Serial.println(" cm");
  Serial.print("Object found in exit at: ");
  Serial.print(distance_out);
  Serial.println(" cm");
  
  counter=0;

  // Check for entrance passage (transition from no object to object detected)
  if (!prev_object_in && curr_object_in) {
    Serial.println("ENTRANCE PASSAGE DETECTED!");
    
    // the following variables are used in order to transform my integer measured value into a uint8_t variable, which is proper for my radio
    char data_read_in[RF22_ROUTER_MAX_MESSAGE_LEN];
    uint8_t data_send_in[RF22_ROUTER_MAX_MESSAGE_LEN];
    memset(data_read_in, '\0', RF22_ROUTER_MAX_MESSAGE_LEN);
    memset(data_send_in, '\0', RF22_ROUTER_MAX_MESSAGE_LEN);    
    sprintf(data_read_in, "%d", "ENTER"); 
    data_read_in[RF22_ROUTER_MAX_MESSAGE_LEN - 1] = '\0'; 
    memcpy(data_send_in, data_read_in, RF22_ROUTER_MAX_MESSAGE_LEN); // now I'm copying data_read to data_send

    if (rf22.sendtoWait(data_read_in, sizeof(data_read_in), DESTINATION_ADDRESS_1) != RF22_ROUTER_ERROR_NONE) { // I'm sending the data in variable data_send to DESTINATION_ADDRESS_1... cross fingers
      Serial.println("sendtoWait failed"); // for some reason I have failed
    }
    else {
      counter=counter+1;
      Serial.println("ENTER message sent successfully");
    }
  }

  // Check for exit passage (transition from no object to object detected)
  if (!prev_object_out && curr_object_out) {
    Serial.println("EXIT PASSAGE DETECTED!");
    
    // the following variables are used in order to transform my integer measured value into a uint8_t variable, which is proper for my radio
    char data_read_out[RF22_ROUTER_MAX_MESSAGE_LEN];
    uint8_t data_send_out[RF22_ROUTER_MAX_MESSAGE_LEN];
    memset(data_read_out, '\0', RF22_ROUTER_MAX_MESSAGE_LEN);
    memset(data_send_out, '\0', RF22_ROUTER_MAX_MESSAGE_LEN);    
    sprintf(data_read_out, "%d", "EXIT");
    data_read_out[RF22_ROUTER_MAX_MESSAGE_LEN - 1] = '\0'; 
    memcpy(data_send_out, data_read_out, RF22_ROUTER_MAX_MESSAGE_LEN); // now I'm copying data_read to data_send

    if (rf22.sendtoWait(data_read_out, sizeof(data_read_out), DESTINATION_ADDRESS_1) != RF22_ROUTER_ERROR_NONE) { // I'm sending the data in variable data_send to DESTINATION_ADDRESS_1... cross fingers
      Serial.println("sendtoWait failed"); // for some reason I have failed
    }
    else {
      counter=counter+1;
      Serial.println("EXIT message sent successfully");
    }
  }
   
  delay(500); // every 0.5 sec 

}