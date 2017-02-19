/* P3S_test
   transmit to/receive from another mbed

 Modification History:
 =================================================================
 Date          Version  Description
 =================================================================
 19 Feb. 2017  1.1      Refactored (delete debug print)
 16 Feb. 2017  1.0      Creation
 -----------------------------------------------------------------
 */

#include "mbed.h"
#include "conf.h"

Serial pc(USBTX, USBRX); // tx, rx
osThreadId mainThreadID;

#if CPU_MODE
DigitalOut sig_out(p10); // signal to H/W
InterruptIn sig_in(p12); // signal from H/W

MemoryPool<frame_t, MPOOL_SIZE> mpool;
Queue<frame_t, QUEUE_SIZE> queue;
Queue<frame_t, QUEUE_SIZE> cleanup_queue;

// Thread IDs
osThreadId appThreadID;
osThreadId cksumThreadID;
osThreadId cleanupThreadID;
#else // HW_MODE
DigitalOut sig_out(p12); // signal to CPU
InterruptIn sig_in(p10); // signal from CPU

// Thread IDs
osThreadId offloadThreadID;
#endif

Timer t;
Timer p_t;

void Rise_interrupt(void);
frame_t* create_frame(void);
void calc_cksum(frame_t* frame);
#if CPU_MODE
void app_thread(void const *argument);
void cksum_thread(void const *argument);
void cleanup_thread(void const *argument);
#else
void offload_thread(void const *argument);
#endif

// main() runs in its own thread in the OS
// (note the calls to wait below for delays)
int main() {
    // attach ISR
    sig_in.rise(&Rise_interrupt);

    mainThreadID = osThreadGetId();

#if CPU_MODE
    Thread app_t(app_thread, NULL, osPriorityHigh, DEFAULT_STACK_SIZE, NULL);
    Thread cksum_t(cksum_thread, NULL, osPriorityHigh, DEFAULT_STACK_SIZE, NULL);
    Thread cleanup_t(cleanup_thread, NULL, osPriorityHigh, DEFAULT_STACK_SIZE, NULL);

    // set priority
    app_t.set_priority(APP_PRIORITY);
    cksum_t.set_priority(CSM_PRIORITY);
    cleanup_t.set_priority(CLU_PRIORITY);

    osSignalSet(appThreadID, START_SIG);
#else
    Thread offload_t(offload_thread, NULL, osPriorityHigh, DEFAULT_STACK_SIZE, NULL);
#endif
    osSignalWait(FINISH_SIG, osWaitForever);

    pc.printf("@main > All finished\r\n");
}

// ISR (Interrupt Service Routine)
void Rise_interrupt(void) {
#if CPU_MODE
    osSignalSet(cksumThreadID, SIGNAL_FROM_HW);
#else
    osSignalSet(offloadThreadID, SIGNAL_FROM_CPU);
#endif
    return;
}

#if CPU_MODE
/** CPU mode **/
void app_thread(void const *argument) {
    int i, j;
    frame_t *frames[NUM_OF_FRAME];

    appThreadID = osThreadGetId();
  #if DEBUG_PRINT
    pc.printf("[CPU_APP] thread ID: %d\r\n", appThreadID);
  #endif

    // data preparation
    for(i=0; i<NUM_OF_FRAME; i++) {
        frames[i] = create_frame();
        if(frames[i] == NULL) {
            pc.printf("[CPU_APP] Create frame failed.\r\n");
            for(j=i; j>0; j--) {
                free(frames[j-1]);
            }
        }
    }

    // -- Start point --
    Thread::signal_wait(START_SIG);
  #if DEBUG_PRINT
    pc.printf("[CPU_APP] Start!\r\n");
  #endif
    t.start();
    // put payload to Queue
    frame_t *frame;
    for(i=0; i<NUM_OF_FRAME; i++) {
        while(1) {
            frame = mpool.alloc();
            if(frame != NULL) {
                break;
            } else {
  #if DEBUG_PRINT
                pc.printf("[CPU_APP] wait MPOOL_FREE_SIG from clup\r\n", i);
  #endif
                Thread::signal_wait(MPOOL_FREE_SIG);
            }
        }
        // memory copy
        memcpy(frame->payload, frames[i]->payload, frames[i]->size);
        frame->size = frames[i]->size;
        while(1) {
            osStatus st = queue.put(frame);
            if(st == osOK) {
  #if DEBUG_PRINT
                pc.printf("[CPU_APP] frame[%d] put queue\r\n", i);
  #endif
                osSignalSet(cksumThreadID, QUEUE_PUT_SIG);
                break;
            } else {
  #if DEBUG_PRINT
                pc.printf("[CPU_APP] wait QUEUE_GET_SIG from cksm\r\n", i);
  #endif
                Thread::signal_wait(QUEUE_GET_SIG);
            }
        }
    }
    Thread::signal_wait(FINISH_SIG);
    for(i=0; i<NUM_OF_FRAME; i++) {
        // free frame data
        free(frames[i]);
    }
    osSignalSet(mainThreadID, FINISH_SIG);
}

void cksum_thread(void const *argument) {
    int i = 0;
    frame_t *frame;
    osEvent evt;

    cksumThreadID = osThreadGetId();
  #if DEBUG_PRINT
    pc.printf("[CPU_SUM] thread ID: %d\r\n", cksumThreadID);
  #endif

    osSignalWait(QUEUE_PUT_SIG, osWaitForever);
    while(1) {
        // get payload from Queue
        while(1) {
            evt = queue.get(0);
            if(evt.status == osEventMessage) {
  #if DEBUG_PRINT
                pc.printf("[CPU_SUM] frame[%d] get from queue\r\n", i);
  #endif
                break;
            } else {
  #if DEBUG_PRINT
                pc.printf("[CPU_SUM] wait QUEUE_PUT_SIG from App.\r\n", i);
  #endif
                osSignalWait(QUEUE_PUT_SIG, osWaitForever);
            }
        }
        osSignalSet(appThreadID, QUEUE_GET_SIG);

  #if HW_OFFLOAD
        frame = (frame_t*)evt.value.p;
        sig_out = 1;
    #if DEBUG_PRINT
        pc.printf("[CPU_SUM] wait signal from H/W\r\n");
    #endif
        osSignalWait(SIGNAL_FROM_HW, osWaitForever);
        sig_out = 0;
    #if DEBUG_PRINT
        pc.printf("[CPU_SUM] signal received from H/W!\r\n");
    #endif
  #else
        frame = (frame_t*)evt.value.p;
        // payload checksum calculation
        calc_cksum(frame);
  #endif

        while(1) {
            osStatus st = cleanup_queue.put(frame);
            if(st == osOK) {
  #if DEBUG_PRINT
                pc.printf("[CPU_SUM] frame[%d] put cleanup queue\r\n", i);
  #endif
                osSignalSet(cleanupThreadID, QUEUE_PUT_SIG);
                break;
            } else {
                Thread::signal_wait(QUEUE_GET_SIG);
            }
        }
        i++;
    }
}

void cleanup_thread(void const *argument) {
    int i;
    osEvent evt;
    frame_t* frame;

    cleanupThreadID = osThreadGetId();
  #if DEBUG_PRINT
    pc.printf("[CPU_CLU] thread ID: %d\r\n", cleanupThreadID);
  #endif

    osSignalWait(QUEUE_PUT_SIG, osWaitForever);
    for(i=0; i<NUM_OF_FRAME; i++) {
        while(1) {
            evt = cleanup_queue.get(0);
            if(evt.status == osEventMessage) {
  #if DEBUG_PRINT
                pc.printf("[CPU_CLU] frame[%d] get from cleanup queue\r\n", i);
  #endif
                break;
            } else {
  #if DEBUG_PRINT
                pc.printf("[CPU_CLU] wait QUEUE_PUT_SIG from cksm\r\n", i);
  #endif
                osSignalWait(QUEUE_PUT_SIG, osWaitForever);
            }
        }
        osSignalSet(cksumThreadID, QUEUE_GET_SIG);

        frame = (frame_t*)evt.value.p;
        mpool.free(frame);
  #if DEBUG_PRINT
        pc.printf("[CPU_CLU] Free frame[%d]\r\n", i);
  #endif
        osSignalSet(appThreadID, MPOOL_FREE_SIG);
    }
    // -- End point --
    t.stop();
    pc.printf("total time: %d usec\r\n", t.read_us());
    t.reset();
    osSignalSet(appThreadID, FINISH_SIG);
}

#else
/** HW mode **/
void offload_thread(void const *argument) {
    int i, j;
    frame_t *frames[NUM_OF_FRAME];

    offloadThreadID = osThreadGetId();

    // data preparation
    for(i=0; i<NUM_OF_FRAME; i++) {
        frames[i] = create_frame();
        if(frames[i] == NULL) {
            pc.printf("[HW_OFFL] Create frame failed.\r\n");
            for(j=i; j>0; j--) {
                free(frames[j-1]);
            }
        }
    }

    pc.printf("[HW_OFFL] Ready to start!\r\n");

    for(i=0; i<NUM_OF_FRAME; i++) {
  #if DEBUG_PRINT
        pc.printf("[HW_OFFL] wait signal from CPU.\r\n");
  #endif
        sig_out = 0;
        osSignalWait(SIGNAL_FROM_CPU, osWaitForever);
  #if DEBUG_PRINT
        pc.printf("[HW_OFFL] signal received from CPU!\r\n");
  #endif
        calc_cksum(frames[i]);
  #if DEBUG_PRINT
        pc.printf("[HW_OFFL] signal send to CPU.\r\n");
  #endif
        sig_out = 1;
    }

    // teardown
    for(i=0; i<NUM_OF_FRAME; i++) {
        free(frames[i]);
    }

    osSignalSet(mainThreadID, FINISH_SIG);
}
#endif /* #if CPU_MODE */

frame_t* create_frame(void) {
    int i;
    frame_t* frame = (frame_t*)malloc(sizeof(frame_t));
    if(frame == NULL) {
        return NULL;
    }
    for(i=0; i<PAYLOAD_SIZE; i++) {
        frame->payload[i] = (char)i%10;
    }
    frame->size = PAYLOAD_SIZE;
    frame->cksm = 0;

    return frame;
}

void calc_cksum(frame_t* frame) {
    int nleft;
    uint16_t *offset;
    uint32_t sum = 0;

    nleft = frame->size;
    offset = (uint16_t*)frame->payload;
    while (nleft > 1) {
        sum += *offset++;
        nleft -= 2;
    }
    if (nleft == 1) {
        *(char *)(&frame->cksm) = *(const char*)offset;
        sum += frame->cksm;
    }
    sum = (sum & 0xffff) + (sum >> 16);
    sum += (sum >> 16);
    frame->cksm = ~sum;
#if DEBUG_PRINT
    pc.printf("@calc_cksum > check sum value: %u\r\n", frame->cksm);
#endif

    return;
}




