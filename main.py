import argparse
import utils as utils
import benchmark as bn

parser = argparse.ArgumentParser(description="Run benchmark and generate plots")
parser.add_argument("-m", "--mode", type=str, choices=["benchmark", "load"], default="benchmark", help="Choose either 'benchmark' to run benchmarks or 'load' to load benchmarks from a CSV file")
parser.add_argument("-n_start", type=int, default=2, help="Starting value for n")
parser.add_argument("-n_step", type=int, default=1, help="Step size for n")
parser.add_argument("-n_steps", type=int, default=5, help="Number of steps for n")
parser.add_argument("-L_start", type=int, default=10, help="Starting value for L")
parser.add_argument("-L_step", type=int, default=10, help="Step size for L")
parser.add_argument("-L_steps", type=int, default=5, help="Number of steps for L")


args = parser.parse_args()

n_values = [args.n_start + i * args.n_step for i in range(args.n_steps)]
L_values = [args.L_start + i * args.L_step for i in range(args.L_steps)]

if args.mode == "benchmark":
    # Running the benchmarks
    setup_times_matrix, aggregate_times_matrix, enc_times_matrix, dec_times_matrix, sizes_crs_matrix, sizes_mpk_matrix = bn.run_benchmarks(L_values, n_values)

    # Converting the sizes of CRS to MB
    sizes_crs_matrix_mb = [[int(size) / (1024 * 1024) for size in row] for row in sizes_crs_matrix]
    sizes_mpk_matrix_mb = [[int(size) / (1024) for size in row] for row in sizes_mpk_matrix]

    # Plotting the heatmaps and 3d plots
    utils.generate_all_plots(L_values, n_values, setup_times_matrix, aggregate_times_matrix, enc_times_matrix, dec_times_matrix, sizes_crs_matrix_mb, sizes_mpk_matrix_mb)
    print("Benchmark results saved in benchmarks.csv and corresponding plots are saved in plots/.")

elif args.mode == "load":
    (L_values, n_values,
     setup_times_matrix, aggregate_times_matrix,
     enc_times_matrix, dec_times_matrix,
     sizes_crs_matrix, sizes_mpk_matrix) = utils.load_benchmarks("benchmarks.csv")
    # Converting the sizes of CRS to MB
    sizes_crs_matrix_mb = [[int(size) / (1024 * 1024) for size in row] for row in sizes_crs_matrix]
    sizes_mpk_matrix_mb = [[int(size) / (1024) for size in row] for row in sizes_mpk_matrix]
    # Plotting the heatmaps and 3d plots
    utils.generate_all_plots(L_values, n_values, setup_times_matrix, aggregate_times_matrix, enc_times_matrix,
                             dec_times_matrix, sizes_crs_matrix_mb, sizes_mpk_matrix_mb)
    print("Plots are saved in plots/ directory.")

