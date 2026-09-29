/* Minimal MPI/node benchmark to compare albedo and levante.
 * pingpong: rank 0 <-> last rank (different nodes), 8 B latency and 1 MiB bandwidth
 * allreduce: 8 B MPI_SUM over all ranks (FESOM ssh solver pattern)
 * halo: each rank exchanges 16 KiB with 6 ring neighbours at distance 1,2,3 (EVP pattern)
 * triad: a[i]=b[i]+s*c[i] on all ranks at once, 32 MiB per rank -> node memory bandwidth
 */
#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static double pingpong(int n, int iters, int me, int other, char *buf) {
    MPI_Barrier(MPI_COMM_WORLD);
    double t0 = MPI_Wtime();
    for (int i = 0; i < iters; i++) {
        if (me == 0) {
            MPI_Send(buf, n, MPI_CHAR, other, 0, MPI_COMM_WORLD);
            MPI_Recv(buf, n, MPI_CHAR, other, 0, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        } else if (me == other) {
            MPI_Recv(buf, n, MPI_CHAR, 0, 0, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
            MPI_Send(buf, n, MPI_CHAR, 0, 0, MPI_COMM_WORLD);
        }
    }
    return (MPI_Wtime() - t0) / iters / 2.0;
}

int main(int argc, char **argv) {
    MPI_Init(&argc, &argv);
    int me, np;
    MPI_Comm_rank(MPI_COMM_WORLD, &me);
    MPI_Comm_size(MPI_COMM_WORLD, &np);
    int last = np - 1;
    char *buf = malloc(1 << 20);
    memset(buf, 1, 1 << 20);

    pingpong(8, 1000, me, last, buf);
    double lat = pingpong(8, 20000, me, last, buf);
    pingpong(1 << 20, 50, me, last, buf);
    double tbw = pingpong(1 << 20, 500, me, last, buf);

    double x = 1.0, y;
    for (int i = 0; i < 200; i++) MPI_Allreduce(&x, &y, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
    MPI_Barrier(MPI_COMM_WORLD);
    double t0 = MPI_Wtime();
    int nar = 5000;
    for (int i = 0; i < nar; i++) MPI_Allreduce(&x, &y, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
    double tar = (MPI_Wtime() - t0) / nar;

    int hn = getenv("HALO_BYTES") ? atoi(getenv("HALO_BYTES")) : 16384, nh = 6;
    char *sb = malloc(hn * nh), *rb = malloc(hn * nh);
    memset(sb, 2, hn * nh);
    MPI_Request req[12];
    int nhalo = 2000;
    for (int rep = 0; rep < 2; rep++) {
        MPI_Barrier(MPI_COMM_WORLD);
        t0 = MPI_Wtime();
        for (int i = 0; i < (rep ? nhalo : 100); i++) {
            int k = 0;
            for (int d = 1; d <= 3; d++) {
                int up = (me + d) % np, dn = (me - d + np) % np;
                MPI_Irecv(rb + (k) * hn, hn, MPI_CHAR, up, d, MPI_COMM_WORLD, &req[k]); k++;
                MPI_Irecv(rb + (k) * hn, hn, MPI_CHAR, dn, d + 10, MPI_COMM_WORLD, &req[k]); k++;
                MPI_Isend(sb + (k - 2) * hn, hn, MPI_CHAR, dn, d, MPI_COMM_WORLD, &req[k + 4]);
                MPI_Isend(sb + (k - 1) * hn, hn, MPI_CHAR, up, d + 10, MPI_COMM_WORLD, &req[k + 5]);
            }
            MPI_Waitall(6, req, MPI_STATUSES_IGNORE);
            MPI_Waitall(6, req + 6, MPI_STATUSES_IGNORE);
        }
    }
    double thalo = (MPI_Wtime() - t0) / nhalo, thmax;
    MPI_Reduce(&thalo, &thmax, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);

    size_t n = 4u << 20; /* 4 Mi doubles = 32 MiB per array */
    double *a = malloc(n * 8), *b = malloc(n * 8), *c = malloc(n * 8);
    for (size_t i = 0; i < n; i++) { a[i] = 0; b[i] = 1; c[i] = 2; }
    double best = 1e9;
    for (int rep = 0; rep < 10; rep++) {
        MPI_Barrier(MPI_COMM_WORLD);
        double t = MPI_Wtime();
        for (size_t i = 0; i < n; i++) a[i] = b[i] + 3.0 * c[i];
        t = MPI_Wtime() - t;
        if (t < best) best = t;
    }
    double bw = 3.0 * n * 8 / best / 1e9, bwsum;
    MPI_Reduce(&bw, &bwsum, 1, MPI_DOUBLE, MPI_SUM, 0, MPI_COMM_WORLD);

    /* cache-resident kernel: 2 x 16 KiB arrays (L1/L2), FMA-heavy, all ranks at once -> core speed */
    int m = 2048; double *p = malloc(m * 8), *q = malloc(m * 8);
    for (int i = 0; i < m; i++) { p[i] = 1.0 + i * 1e-9; q[i] = 0.5; }
    double cbest = 1e9;
    for (int rep = 0; rep < 5; rep++) {
        MPI_Barrier(MPI_COMM_WORLD);
        double t = MPI_Wtime();
        for (int it = 0; it < 20000; it++)
            for (int i = 0; i < m; i++) p[i] = p[i] * 0.999999 + q[i] * 1e-7;
        t = MPI_Wtime() - t;
        if (t < cbest) cbest = t;
    }
    double gf = 2.0 * m * 20000 / cbest / 1e9, gfsum;
    MPI_Reduce(&gf, &gfsum, 1, MPI_DOUBLE, MPI_SUM, 0, MPI_COMM_WORLD);
    if (me == 0) printf("CORE ranks=%d  cache_kernel_GFlops_per_rank=%.3f  (check %g)\n", np, gfsum / np, p[5]);

    char host[MPI_MAX_PROCESSOR_NAME]; int hl;
    MPI_Get_processor_name(host, &hl);
    if (me == 0) {
        printf("RESULT ranks=%d  pingpong_8B_us=%.2f  pingpong_1MiB_GBs=%.2f  allreduce_8B_us=%.2f  halo6x%dB_us=%.1f  triad_GBs_per_rank=%.2f  (check=%g %c)\n",
               np, lat * 1e6, (1 << 20) / tbw / 1e9, tar * 1e6, hn, thmax * 1e6, bwsum / np, y, a[7] > 0 ? 'y' : 'n');
    }
    MPI_Finalize();
    return 0;
}
