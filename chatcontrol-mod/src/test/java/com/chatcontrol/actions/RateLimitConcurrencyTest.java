package com.chatcontrol.actions;

import org.junit.jupiter.api.Test;

import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

import static org.junit.jupiter.api.Assertions.*;

class RateLimitConcurrencyTest {

    @Test
    void testConcurrentIncrements() throws InterruptedException {
        final int THREAD_COUNT = 10;
        final int INCREMENTS_PER_THREAD = 100;
        final AtomicInteger counter = new AtomicInteger(0);
        final AtomicInteger maxObserved = new AtomicInteger(0);

        ExecutorService executor = Executors.newFixedThreadPool(THREAD_COUNT);
        CountDownLatch latch = new CountDownLatch(THREAD_COUNT);

        for (int t = 0; t < THREAD_COUNT; t++) {
            executor.submit(() -> {
                for (int i = 0; i < INCREMENTS_PER_THREAD; i++) {
                    int val = counter.incrementAndGet();
                    int currentMax;
                    do {
                        currentMax = maxObserved.get();
                        if (val <= currentMax) break;
                    } while (!maxObserved.compareAndSet(currentMax, val));
                }
                latch.countDown();
            });
        }

        latch.await(5, TimeUnit.SECONDS);
        executor.shutdown();

        assertEquals(THREAD_COUNT * INCREMENTS_PER_THREAD, counter.get());
        assertEquals(THREAD_COUNT * INCREMENTS_PER_THREAD, maxObserved.get());
    }

    @Test
    void testAtomicIntegerThreadSafety() throws InterruptedException {
        final int THREAD_COUNT = 8;
        final int ITERATIONS = 1000;
        final AtomicInteger counter = new AtomicInteger(0);

        ExecutorService executor = Executors.newFixedThreadPool(THREAD_COUNT);
        CountDownLatch latch = new CountDownLatch(THREAD_COUNT);

        for (int t = 0; t < THREAD_COUNT; t++) {
            executor.submit(() -> {
                for (int i = 0; i < ITERATIONS; i++) {
                    counter.incrementAndGet();
                }
                latch.countDown();
            });
        }

        latch.await(5, TimeUnit.SECONDS);
        executor.shutdown();

        assertEquals(THREAD_COUNT * ITERATIONS, counter.get());
    }

    @Test
    void testAtomicLongCAS() throws InterruptedException {
        final int THREAD_COUNT = 8;
        final int ITERATIONS = 500;
        final AtomicLong value = new AtomicLong(0);

        ExecutorService executor = Executors.newFixedThreadPool(THREAD_COUNT);
        CountDownLatch latch = new CountDownLatch(THREAD_COUNT);

        for (int t = 0; t < THREAD_COUNT; t++) {
            final int threadId = t;
            executor.submit(() -> {
                for (int i = 0; i < ITERATIONS; i++) {
                    long current;
                    do {
                        current = value.get();
                    } while (!value.compareAndSet(current, current + 1));
                }
                latch.countDown();
            });
        }

        latch.await(5, TimeUnit.SECONDS);
        executor.shutdown();

        assertEquals(THREAD_COUNT * ITERATIONS, value.get());
    }
}
