#ifndef __CONF_H__
#define __CONF_H__

#define DEBUG_PRINT       0

#define CPU_MODE          0
#if CPU_MODE
  #define HW_OFFLOAD      1
  #define APP_PRIORITY    osPriorityNormal
  #define CSM_PRIORITY    osPriorityHigh
  #define CLU_PRIORITY    osPriorityLow
#endif

#define PAYLOAD_SIZE    512
#define NUM_OF_FRAME     10

#define MPOOL_SIZE        5
#define QUEUE_SIZE        5

#define MPOOL_FREE_SIG  0x1
#define QUEUE_PUT_SIG   0x2
#define QUEUE_GET_SIG   0x3
#define START_SIG       0x4
#define FINISH_SIG      0x5

#define SIGNAL_FROM_HW  0x6
#define SIGNAL_FROM_CPU 0x7

typedef struct {
    char payload[PAYLOAD_SIZE];
    uint16_t cksm;
    uint16_t size;
} frame_t;

#endif

