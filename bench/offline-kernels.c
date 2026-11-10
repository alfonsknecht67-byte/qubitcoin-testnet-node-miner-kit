/* Isolated component benchmark: no miner main, sockets, RPC or submissions. */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "algo/qhash/qhash-gate.h"
#include "algo/deqode/deqode-gate.h"

static double now(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) exit(2);
    return (double)t.tv_sec + (double)t.tv_nsec / 1e9;
}

static int fail(const char *message) { fprintf(stderr, "%s\n", message); return 2; }

static int qhash(unsigned rounds) {
    unsigned char data[64] = {0};
    double values[NUM_QUBITS], previous[NUM_QUBITS], checksum = 0;
    if (!qhash_cpu_thread_init(0)) return fail("QHash allocation failed");
    run_simulation_cpu(data, 0, values);
    for (int q = 0; q < NUM_QUBITS; ++q)
        if (fabs(values[q] - 1.0) > 1e-12) return fail("QHash zero-angle fixture failed");
    for (int i = 0; i < 64; ++i) data[i] = (unsigned char)(17*i+3);
    run_simulation_cpu(data, 1, previous);
    run_simulation_cpu(data, 1, values);
    for (int q = 0; q < NUM_QUBITS; ++q)
        if (!isfinite(values[q]) || fabs(values[q]) > 1.000000001 || values[q] != previous[q])
            return fail("QHash repeatability fixture failed");
    const double start = now();
    for (unsigned i = 0; i < rounds; ++i) {
        run_simulation_cpu(data, i & 1, values);
        for (int q = 0; q < NUM_QUBITS; ++q) checksum += values[q];
    }
    double seconds = now() - start;
    printf("{\"task\":\"qhash-cpu\",\"fixture\":\"circuit16-layers2-v1\","
           "\"units\":%u,\"unit\":\"circuit_simulations\",\"seconds\":%.9f,"
           "\"checksum\":%.17g,\"correctness_checks\":true}\n", rounds, seconds, checksum);
    return 0;
}

typedef struct { const dq_code *code; const uint64_t *targets; int w; size_t count; unsigned witnesses; int invalid; } context;

static bool witness(void *ptr, size_t index, const uint64_t *x, const uint64_t *z) {
    context *c = ptr;
    if (index >= c->count) { c->invalid = 1; return true; }
    uint64_t syn[DQ_WORDS(DQ_MAX_QUBITS)] = {0};
    unsigned weight = 0;
    for (int q = 0; q < c->code->n; ++q) {
        const int xb = (x[q/64] >> (q%64)) & 1, zb = (z[q/64] >> (q%64)) & 1;
        weight += xb || zb;
        for (size_t j = 0; j < c->code->rw; ++j) {
            if (xb) syn[j] ^= c->code->col_z[(size_t)q*c->code->rw+j];
            if (zb) syn[j] ^= c->code->col_x[(size_t)q*c->code->rw+j];
        }
    }
    if (weight > (unsigned)c->w || memcmp(syn, c->targets+index*c->code->rw, c->code->rw*8)) {
        c->invalid = 1;
        return true;
    }
    ++c->witnesses;
    return false;
}

static int deqode(unsigned rounds) {
    dq_params params = {32,16,2,24};
    dq_tuning tuning = {1,1,4,4*1024*1024,32};
    dq_code code = {0};
    const unsigned char seed[32] = {1,2,3,4,5,6,7,8};
    if (!dq_code_alloc(&code, params.n, params.r)) return fail("Code allocation failed");
    dq_derive_columns(&code, seed, sizeof(seed), params.gate_multiplier);
    struct dq_solver *solver = dq_solver_new(&params, &tuning, UINT64_C(0x123456789abcdef));
    if (!solver) { dq_code_free(&code); return fail("Solver allocation failed"); }
    uint64_t targets[32] = {0};
    for (int i = 0; i < 32; ++i) targets[i] = code.col_z[i];
    context c = {&code, targets, params.w, 32, 0, 0};
    const uint64_t planted_x = 1, planted_z = 0;
    witness(&c, 0, &planted_x, &planted_z);
    if (c.invalid || c.witnesses != 1) return fail("Planted witness fixture failed");
    c.witnesses = 0;
    const double start = now();
    for (unsigned i = 0; i < rounds; ++i) {
        if (!dq_solver_new_information_set(solver, &code)) return fail("Information-set creation failed");
        double progress = 0;
        dq_solver_join_batch(solver, targets, 32, witness, &c, NULL, &progress);
        if (c.invalid || fabs(progress - 1.0) > 1e-12) return fail("Solver witness/progress check failed");
    }
    const double seconds = now() - start;
    dq_solver_free(solver); dq_code_free(&code);
    if (!c.witnesses) return fail("Fixture produced no validated solver witness");
    printf("{\"task\":\"deqode\",\"fixture\":\"n32-r16-w2-gm24-p1-1-l4-mem4-b32-seed1-v1\","
           "\"units\":%u,\"unit\":\"syndromes_processed\",\"seconds\":%.9f,"
           "\"validated_witnesses\":%u,\"correctness_checks\":true}\n", rounds*32, seconds, c.witnesses);
    return 0;
}

int main(int argc, char **argv) {
    if (argc != 3) return fail("Usage: qtc-offline-kernels TASK ROUNDS");
    char *end; unsigned long rounds = strtoul(argv[2], &end, 10);
    if (!*argv[2] || *end || rounds < 1 || rounds > 10000) return fail("ROUNDS must be 1..10000");
    if (!strcmp(argv[1], "qhash-cpu")) return qhash((unsigned)rounds);
    if (!strcmp(argv[1], "deqode")) return deqode((unsigned)rounds);
    return fail("Unknown task");
}
