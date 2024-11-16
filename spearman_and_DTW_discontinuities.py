

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from scipy.signal import find_peaks, savgol_filter
from scipy.stats import spearmanr
import seaborn as sns

import matplotlib as mpl
mpl.use('SVG')
mpl.rcParams['svg.fonttype'] = 'none'


#%% THINGS TO CHANGE
file_path = '...scorestxt'
data = pd.read_csv(file_path, delim_whitespace=True, header=None)
cmap = 'magma'

time = data[0].values[:] * 1.1
#time = data[0].index() * 1.1
pc1 = data[1].values[:]

window_length = 5  # SG 
polyorder = 2 #SG
peak_threshold = 15 #detect peaks with magnitude beyond this value
trough_threshold = 15#detect troughs with magnitude beyond this value
magnitude_threshold = 2#detect changes in trend by comparing the differnece between (i-1) and i vs (i+1) and i. if difference is more than 3*magnitude_threshold, it is a discontinuity

folder = os.path.dirname(file_path)
folder_path = os.path.join(folder, 'PC1_discontinuities/areas')
#folder_path = os.path.join(folder, 'PC1_discontinuities/pH')
#folder_path = os.path.join(folder, 'PC1_discontinuities/stark')

os.makedirs(folder_path, exist_ok=True)
filename = os.path.basename(folder) + "_PC1_with_discontinuities_areas"
#filename = os.path.basename(folder) + "_PC1_with_discontinuities_pH"
#filename = os.path.basename(folder) + "_PC1_with_discontinuities_stark"


# Find the corresponding integrated areas file in the subfolder 1101_to_3999
def find_integrated_areas_file(file_path):
    base_folder = os.path.dirname(file_path)
    subfolder = '1101_to_3999'
    #subfolder = '1101_to_3999'
    #subfolder = 'CO_peak'
    folder_path = os.path.join(base_folder, subfolder)
    
    # Search for the file ending with 'integrated_areas.csv'
    for file_name in os.listdir(folder_path):
        if file_name.endswith('integrated_areas.csv'):
        #if file_name.endswith('1430_1368.csv'):
        #if file_name.endswith('peak_shift.csv'):

            return os.path.join(folder_path, file_name)
    
    raise FileNotFoundError("Integrated areas file not found") # in case


#%%
pc1_smoothed = savgol_filter(pc1, window_length=window_length, polyorder=polyorder)

potential_change_times = np.array([100, 200, 300, 400, 500, 600, 700, 800, 900, 1000])

def calculate_discontinuity_magnitudes(time, pc1_smoothed, discontinuities):
    magnitudes = []
    for i in discontinuities:
        if i > 0 and i < len(pc1_smoothed) - 1:
            # Calculate the magnitude of the discontinuity
            magnitude_before = abs(pc1_smoothed[i] - pc1_smoothed[i-1])
            magnitude_after = abs(pc1_smoothed[i] - pc1_smoothed[i+1])
            magnitude = max(magnitude_before, magnitude_after)
            magnitudes.append(magnitude)
    return np.array(magnitudes)

def analyze_discontinuities(time, pc1_smoothed, peak_threshold=peak_threshold, trough_threshold=trough_threshold, 
                            potential_change_times=None, magnitude_threshold=magnitude_threshold):
    time_adjusted = time
    
    peaks, _ = find_peaks(pc1_smoothed, prominence=peak_threshold)
    troughs, _ = find_peaks(-pc1_smoothed, prominence=trough_threshold)
    discontinuities = np.sort(np.concatenate((peaks, troughs)))
    
    # Detect discontinuities
    custom_discontinuities = []
    for i in range(1, len(pc1_smoothed) - 1):
        diff_before = abs(pc1_smoothed[i] - pc1_smoothed[i-1])
        diff_after = abs(pc1_smoothed[i+1] - pc1_smoothed[i])
        if diff_after >= 3 * diff_before:
            custom_discontinuities.append(i)
    
    # Combine custom discontinuities with existing ones
    discontinuities = np.unique(np.concatenate((discontinuities, custom_discontinuities)))
    
    # Filter out discontinuities near potential change points
    if potential_change_times is not None:
        potential_change_indices = [np.argmin(np.abs(time_adjusted - pct)) for pct in potential_change_times]
        mask = np.ones(len(discontinuities), dtype=bool)
        for i in potential_change_indices:
            mask &= (np.abs(discontinuities - i) > 15)
        discontinuities = discontinuities[mask]
    
    # Calculate the magnitude of discontinuities
    magnitudes = calculate_discontinuity_magnitudes(time, pc1_smoothed, discontinuities)
    
    # Filter out discontinuities with magnitude below the threshold
    valid_indices = magnitudes >= magnitude_threshold
    discontinuities = discontinuities[valid_indices]
    magnitudes = magnitudes[valid_indices]
    
    return time_adjusted[discontinuities], magnitudes, pc1_smoothed[discontinuities], potential_change_times

disc_times, disc_magnitudes, disc_values, potential_changes = analyze_discontinuities(
    time, pc1_smoothed, 
    peak_threshold=peak_threshold, 
    trough_threshold=trough_threshold, 
    potential_change_times=potential_change_times, 
    magnitude_threshold=magnitude_threshold)

print(f"Number of discontinuities: {len(disc_magnitudes)}")
print(f"Average magnitude of discontinuities: {np.mean(disc_magnitudes):.2f}")
print(f"Standard deviation of magnitude: {np.std(disc_magnitudes):.2f}")
print("\nDiscontinuity details (Time, Magnitude, Value):")
for t, mag, val in zip(disc_times, disc_magnitudes, disc_values):
    print(f"Time: {t:.2f}, Magnitude: {mag:.2f}, Value: {val:.2f}")    

colors = ['#2c3e50', '#e74c3c']  # Dark blue and red

labels = ['PC1', 'Discontinuities']

fig, ax = plt.subplots(figsize=(12, 8))

ax.plot(time, pc1_smoothed, label=labels[0], color=colors[0], linewidth=2)

ax.scatter(disc_times, pc1_smoothed[np.searchsorted(time, disc_times)],
           color=colors[1], edgecolor='black', linewidth=1.5, s=100, label=labels[1])

if potential_changes is not None:
    for pct_time in potential_changes:
        ax.axvline(x=pct_time, color='g', linestyle='--', alpha=0.5)

ax.set_xlabel('Time (s)', fontsize=18)
ax.set_ylabel('PC1', fontsize=18)
ax.set_title('PC1 with Identified Discontinuities', fontsize=18)
#ax.invert_xaxis()
ax.legend(fontsize=18)
ax.set_xlim(time[0], time[-1])
ax.grid(False)

message1 = f"Number of discontinuities: {len(disc_magnitudes)}"
message2 = f"Average magnitude: {np.mean(np.abs(disc_magnitudes)):.2f}"
message3 = f"Standard deviation of magnitude: {np.std(np.abs(disc_magnitudes)):.2f}"
ax.text(0.05, 0.95, message1, transform=ax.transAxes, fontsize=14, verticalalignment='top')
ax.text(0.05, 0.90, message2, transform=ax.transAxes, fontsize=14, verticalalignment='top')
ax.text(0.05, 0.85, message3, transform=ax.transAxes, fontsize=14, verticalalignment='top')

plt.tight_layout()

png_path = os.path.join(folder_path, f"{filename}.png")
svg_path = os.path.join(folder_path, f"{filename}.svg")

plt.savefig(png_path)
plt.savefig(svg_path, format='svg', transparent=True)
plt.show()

#%% comparing the discontinuities with the integrated areas

def get_surrounding_points(time, pc1_smoothed, discontinuities, window=5): #extract the values nearby the discontinuities
    surrounding_times = []
    surrounding_values = []
    surrounding_indices = []
    
    discontinuity_indices = np.searchsorted(time, discontinuities) # Convert discontinuity times to indices
    
    for i in discontinuity_indices:
        # Ensure you don't go out of bounds
        start = max(i - window, 0)
        end = min(i + window + 1, len(pc1_smoothed))
        
        # Append the time points, smoothed values, and indices
        surrounding_times.append(time[start:end])
        surrounding_values.append(pc1_smoothed[start:end])
        surrounding_indices.append(np.arange(start, end))  # Store the indices
    
    return surrounding_times, surrounding_values, surrounding_indices

surrounding_times, surrounding_values, surrounding_indices = get_surrounding_points(time, pc1_smoothed, disc_times)

for i, (times, values, indices) in enumerate(zip(surrounding_times, surrounding_values, surrounding_indices)): #print those values
    print(f"Discontinuity {i+1}:")
    print(f"Surrounding Time Points: {times}")
    print(f"Surrounding Values: {values}")
    print(f"Surrounding Indices: {indices}")



integrated_areas_file = find_integrated_areas_file(file_path)
integrated_areas_data = pd.read_csv(integrated_areas_file, header=0, usecols=lambda col: col != 'Time (s)')  # The header contains peak positions

def calculate_spearman_for_discontinuities(surrounding_values, surrounding_indices, integrated_areas_data):
    spearman_coefficients = {}
    for i, indices in enumerate(surrounding_indices):
        spearman_coefficients[f'Discontinuity_{i+1}'] = {}
        
        adjusted_indices = indices + 1
        
        # Loop each peak
        for peak in integrated_areas_data.columns:
            integrated_values = integrated_areas_data[peak].values[adjusted_indices]
            
            # Calculate Spearman correlation between surrounding PCA values and integrated areas values
            pca_values = surrounding_values[i]
            if len(pca_values) == len(integrated_values):  # Ensure both have the same length
                spearman_corr, _ = spearmanr(pca_values, integrated_values)
                spearman_coefficients[f'Discontinuity_{i+1}'][peak] = spearman_corr
    
    return spearman_coefficients

# Call the function
spearman_results = calculate_spearman_for_discontinuities(surrounding_values, surrounding_indices, integrated_areas_data)


def plot_spearman_visualization(pca_values, integrated_values, discontinuity_time, output_folder):
    # Ensure that pca_values and integrated_values have the same size
    if len(pca_values) != len(integrated_values):
        min_len = min(len(pca_values), len(integrated_values))
        pca_values = pca_values[:min_len]
        integrated_values = integrated_values[:min_len]
    
    plt.figure(figsize=(8, 6))
    plt.scatter(pca_values, integrated_values, color='blue')
    plt.title(f'PCA vs Integrated Areas (Discontinuity: {discontinuity_time:.2f} s)')
    plt.xlabel('PCA Values')
    plt.ylabel('Integrated Areas')
    plt.grid(True)

    pca_ranks = np.argsort(pca_values) + 1
    integrated_ranks = np.argsort(integrated_values) + 1

    for i, (pca, int_area) in enumerate(zip(pca_values, integrated_values)):
        plt.text(pca, int_area, f'({pca_ranks[i]},{integrated_ranks[i]})', fontsize=9, ha='right')

    plt.tight_layout()
    raw_plot_path = os.path.join(output_folder, f'spearman_raw_ranks_{discontinuity_time:.2f}.png')
    plt.savefig(raw_plot_path, dpi=300)
    plt.close()

    plt.figure(figsize=(8, 6))
    plt.scatter(pca_values, integrated_values, color='blue')
    plt.title(f'PCA vs Integrated Areas with Rank Differences (Discontinuity: {discontinuity_time:.2f} s)')
    plt.xlabel('PCA Values')
    plt.ylabel('Integrated Areas')
    plt.grid(True)

    for i in range(len(pca_values)):
        pca_rank = pca_ranks[i]
        int_rank = integrated_ranks[i]
        plt.arrow(pca_values[i], integrated_values[i], 0, (int_rank - pca_rank) * 0.05, 
                  head_width=0.1, head_length=0.05, fc='red', ec='red')

    plt.tight_layout()
    rank_diff_plot_path = os.path.join(output_folder, f'spearman_rank_differences_{discontinuity_time:.2f}.png')
    plt.savefig(rank_diff_plot_path, dpi=300)
    plt.close()

    spearman_corr, _ = spearmanr(pca_values, integrated_values)

    plt.figure(figsize=(8, 6))
    plt.scatter(pca_values, integrated_values, color='blue')
    plt.title(f'Spearman Correlation Calculation (Discontinuity: {discontinuity_time:.2f} s)')
    plt.xlabel('PCA Values')
    plt.ylabel('Integrated Areas')
    plt.grid(True)

    formula_text = r'$\rho = 1 - \frac{6 \sum d_i^2}{n(n^2 - 1)}$'
    plt.text(0.05, 0.95, f'{formula_text}\nSpearman Correlation: {spearman_corr:.2f}', 
             transform=plt.gca().transAxes, fontsize=12, verticalalignment='top')

    plt.tight_layout()
    spearman_final_plot_path = os.path.join(output_folder, f'spearman_final_{discontinuity_time:.2f}.png')
    plt.savefig(spearman_final_plot_path, dpi=300)
    plt.close()

def plot_spearman_visualization_with_arrows(pca_values, integrated_values, discontinuity_time, output_folder):
    # Ensure that pca_values and integrated_values have the same size
    if len(pca_values) != len(integrated_values):
        min_len = min(len(pca_values), len(integrated_values))
        pca_values = pca_values[:min_len]
        integrated_values = integrated_values[:min_len]
    
    plt.figure(figsize=(8, 6))
    plt.scatter(pca_values, integrated_values, color='blue')
    plt.title(f'PCA vs Integrated Areas with Rank Differences (Discontinuity: {discontinuity_time:.2f} s)')
    plt.xlabel('PCA Values')
    plt.ylabel('Integrated Areas')
    plt.grid(True)

    pca_ranks = np.argsort(pca_values) + 1
    integrated_ranks = np.argsort(integrated_values) + 1

    for i, (pca, int_area) in enumerate(zip(pca_values, integrated_values)):
        plt.text(pca, int_area, f'({pca_ranks[i]},{integrated_ranks[i]})', fontsize=9, ha='right')

    for i in range(len(pca_values)):
        pca_rank = pca_ranks[i]
        int_rank = integrated_ranks[i]
        rank_diff = int_rank - pca_rank
        plt.arrow(pca_values[i], integrated_values[i], 0, rank_diff * 0.05, 
                  head_width=0.1, head_length=0.05, fc='red', ec='red')
        plt.text(pca_values[i], integrated_values[i] + rank_diff * 0.025, f'd={rank_diff}', fontsize=9, ha='center', color='green')

    spearman_corr, _ = spearmanr(pca_values, integrated_values)

    # Final plot showing the formula and result
    formula_text = r'$\rho = 1 - \frac{6 \sum d_i^2}{n(n^2 - 1)}$'
    plt.text(0.05, 0.95, f'{formula_text}\nSpearman Correlation: {spearman_corr:.2f}', 
             transform=plt.gca().transAxes, fontsize=12, verticalalignment='top')

    # Save the final plot
    plt.tight_layout()
    spearman_final_plot_path = os.path.join(output_folder, f'spearman_with_arrows_{discontinuity_time:.2f}.png')
    plt.savefig(spearman_final_plot_path, dpi=300)
    plt.close()

    print(f"Spearman visualizations with rank differences saved to: {output_folder}")


def explain_spearman_visualization(pca_values, integrated_values, discontinuity_time, output_folder):
    # Ensure that pca_values and integrated_values have the same size
    if len(pca_values) != len(integrated_values):
        min_len = min(len(pca_values), len(integrated_values))
        pca_values = pca_values[:min_len]
        integrated_values = integrated_values[:min_len]

    pca_ranks = np.argsort(pca_values) + 1
    integrated_ranks = np.argsort(integrated_values) + 1
    rank_diffs = integrated_ranks - pca_ranks
    rank_diffs_squared = rank_diffs ** 2
    sum_squared_diffs = np.sum(rank_diffs_squared)
    n = len(pca_values)
    
    spearman_corr = 1 - (6 * sum_squared_diffs) / (n * (n**2 - 1))

    plt.figure(figsize=(10, 6))
    plt.scatter(pca_values, integrated_values, color='blue', s=100, edgecolor='black')
    plt.title(f'PCA vs Integrated Areas with Ranks (Discontinuity: {discontinuity_time:.2f} s)')
    plt.xlabel('PCA Values')
    plt.ylabel('Integrated Areas')
    plt.grid(True)

    for i, (pca, int_area) in enumerate(zip(pca_values, integrated_values)):
        plt.text(pca, int_area, f'({pca_ranks[i]},{integrated_ranks[i]})', fontsize=9, ha='right')
    
    for i in range(len(pca_values)):
        pca_rank = pca_ranks[i]
        int_rank = integrated_ranks[i]
        rank_diff = int_rank - pca_rank
        plt.arrow(pca_values[i], integrated_values[i], 0, rank_diff * 0.05, 
                  head_width=0.1, head_length=0.05, fc='red', ec='red')
        plt.text(pca_values[i], integrated_values[i] + rank_diff * 0.025, f'd={rank_diff}', fontsize=9, ha='center', color='green')

    # Display the formula and final Spearman Correlation
    formula_text = r'$\rho = 1 - \frac{6 \sum d_i^2}{n(n^2 - 1)}$'
    plt.text(0.05, 0.95, f'{formula_text}\nSpearman Correlation: {spearman_corr:.2f}', 
             transform=plt.gca().transAxes, fontsize=12, verticalalignment='top')

    # Save the final plot
    plt.tight_layout()
    spearman_final_plot_path = os.path.join(output_folder, f'spearman_explanation_{discontinuity_time:.2f}.png')
    spearman_final_plot_path_svg = os.path.join(output_folder, f'spearman_explanation_{discontinuity_time:.2f}.svg')
    plt.savefig(spearman_final_plot_path, dpi=300)
    plt.savefig(spearman_final_plot_path_svg, format='svg')
    plt.close()

    print(f"Spearman visual explanation saved to: {spearman_final_plot_path}")

output_folder = os.path.join(folder_path, 'Spearman_Visualizations')
os.makedirs(output_folder, exist_ok=True)

for i, (pca_values, int_values, time) in enumerate(zip(surrounding_values, integrated_areas_data.values, disc_times)):
    plot_spearman_visualization(pca_values, int_values, time, output_folder)
for i, (pca_values, int_values, time) in enumerate(zip(surrounding_values, integrated_areas_data.values, disc_times)):
    plot_spearman_visualization_with_arrows(pca_values, int_values, time, output_folder)
for i, (pca_values, int_values, time) in enumerate(zip(surrounding_values, integrated_areas_data.values, disc_times)):
    explain_spearman_visualization(pca_values, int_values, time, output_folder)
    
for discontinuity, correlations in spearman_results.items():
    print(f"\n{discontinuity}:")
    for peak, coeff in correlations.items():
        print(f"Peak {peak}: Spearman Coefficient = {coeff:.2f}")

# Prepare the data for the heatmap plot
def prepare_spearman_matrix(spearman_results):
    discontinuities = list(spearman_results.keys())
    peaks = list(next(iter(spearman_results.values())).keys())  # Assume all discontinuities have the same peaks
    
    matrix = np.zeros((len(discontinuities), len(peaks)))
    for i, disc in enumerate(discontinuities):
        for j, peak in enumerate(peaks):
            matrix[i, j] = spearman_results[disc][peak]
    
    return matrix, discontinuities, peaks


# Generate the spearman matrix and labels
discontinuity_times = [f"{time:.2f} s" for time in disc_times]
matrix, discontinuities, peaks = prepare_spearman_matrix(spearman_results)

plt.figure(figsize=(14, 8))  # Adjust the figure size for better visibility
ax = sns.heatmap(matrix, cmap=cmap, annot=True, cbar=True, 
                 xticklabels=peaks, yticklabels=discontinuity_times, 
                 linewidths=0.5, annot_kws={"size": 10},  # Annotation font size
                 cbar_kws={"shrink": 0.8, "ticks": [-1, -0.5, 0, 0.5, 1]})  # Tweak color bar

ax.set_xlabel('FTIR Peaks', fontsize=14, labelpad=20)  # Increase x-axis label size and add padding
ax.set_ylabel('Discontinuities', fontsize=14, labelpad=10)  # Increase y-axis label size
ax.set_title('Spearman Correlation Coefficients', fontsize=18, pad=20)  # Title size and padding

plt.xticks(rotation=45, ha='right', fontsize=10)  # Rotate x-axis labels for better readability
plt.yticks(fontsize=10)  # Adjust y-axis label size

cbar = ax.collections[0].colorbar
cbar.ax.tick_params(labelsize=10)  # Set color bar tick size

plt.tight_layout()


os.makedirs(folder, exist_ok=True)

figure_filename_png = os.path.join(folder_path, 'Spearman_Correlation_Matrix.png')
figure_filename_svg = os.path.join(folder_path, 'Spearman_Correlation_Matrix.svg')
plt.savefig(figure_filename_png, dpi=300)  # Save as PNG with high resolution
plt.savefig(figure_filename_svg, format='svg')  # Save as SVG
plt.show()

plt.show()

spearman_df = pd.DataFrame(spearman_results).T  # Transpose to have peaks as columns
spearman_df.index = discontinuity_times
discontinuity_info = pd.DataFrame({
    'Discontinuity Time (s)': discontinuity_times,
    'Discontinuity Magnitude': disc_magnitudes,
    'Discontinuity Value': disc_values
})

if len(disc_magnitudes) > 0:
    avg_magnitude = np.mean(disc_magnitudes)
    std_magnitude = np.std(disc_magnitudes)
else:
    avg_magnitude = "No discontinuities"
    std_magnitude = "No discontinuities"

# Create a metadata dictionary
metadata = {
    'SG Filter Window Length': [window_length],
    'SG Filter Polyorder': [polyorder],
    'Peak Threshold': [peak_threshold],
    'Trough Threshold': [trough_threshold],
    'Magnitude Threshold': [magnitude_threshold],
    'Average Discontinuity Magnitude': [avg_magnitude],
    'Standard Deviation of Discontinuity Magnitude': [std_magnitude]
}

# Convert the metadata dictionary to a DataFrame
metadata_df = pd.DataFrame(metadata)

# Calculate the column-wise averages for Spearman coefficients
spearman_averages = spearman_df.mean()

# Add the averages as a new row at the bottom of the Spearman DataFrame
spearman_df.loc['Average'] = spearman_averages

# Save everything to a CSV file
csv_filename = os.path.join(folder_path, 'Spearman_Correlation_Report.csv')

# Open a writer to concatenate all sections of the report
with open(csv_filename, 'w') as f:
    # Save the metadata
    metadata_df.to_csv(f, index=False)
    
    f.write("\n")  # Add some space between sections
    
    # Save the discontinuity information
    discontinuity_info.to_csv(f, index=False)
    
    f.write("\n")  # Add some space between sections
    
    # Save the Spearman correlation matrix with the averages
    spearman_df.to_csv(f, index_label='Discontinuity Time (s)')

# Print a message to confirm
print(f"Spearman correlation report saved to {csv_filename}")

#%% DTW from here downwards

import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import os

def dp(dist_mat):
    """
    Find minimum-cost path through matrix `dist_mat` using dynamic programming.
    """
    N, M = dist_mat.shape
    cost_mat = np.zeros((N + 1, M + 1))
    for i in range(1, N + 1):
        cost_mat[i, 0] = np.inf
    for i in range(1, M + 1):
        cost_mat[0, i] = np.inf

    traceback_mat = np.zeros((N, M))
    for i in range(N):
        for j in range(M):
            penalty = [
                cost_mat[i, j],      # match
                cost_mat[i, j + 1],  # insertion
                cost_mat[i + 1, j]]  # deletion
            i_penalty = np.argmin(penalty)
            cost_mat[i + 1, j + 1] = dist_mat[i, j] + penalty[i_penalty]
            traceback_mat[i, j] = i_penalty

    i, j = N - 1, M - 1
    path = [(i, j)]
    while i > 0 or j > 0:
        tb_type = traceback_mat[i, j]
        if tb_type == 0:
            i -= 1
            j -= 1
        elif tb_type == 1:
            i -= 1
        elif tb_type == 2:
            j -= 1
        path.append((i, j))
    cost_mat = cost_mat[1:, 1:]
    return (path[::-1], cost_mat)

def plot_dtw_matrices_and_path(dist_mat, cost_mat, path, x, y, output_folder, file_suffix):
    """
    Plot the distance matrix, cost matrix, and alignment path, and save the figures.
    """
    # Plot the distance matrix and cost matrix
    fig, ax = plt.subplots(figsize=(10, 8))
    plt.subplot(121)
    plt.title("Distance Matrix")
    plt.imshow(dist_mat, cmap=plt.cm.binary, interpolation="nearest", origin="lower")
    plt.subplot(122)
    plt.title("Cost Matrix")
    plt.imshow(cost_mat, cmap=plt.cm.binary, interpolation="nearest", origin="lower")
    x_path, y_path = zip(*path)
    plt.plot(y_path, x_path)
    
    plt.tight_layout()
    dist_cost_plot_path = os.path.join(output_folder, f"DTW_Matrices_{file_suffix}.png")
    plt.savefig(dist_cost_plot_path, dpi=300)
    plt.close()

    fig, ax = plt.subplots(figsize=(10, 8))
    for x_i, y_j in path:
        plt.plot([x_i, y_j], [x[x_i] + 1.5, y[y_j] - 1.5], c="C7")
    plt.plot(np.arange(x.shape[0]), x + 1.5, "-o", c="C3")
    plt.plot(np.arange(y.shape[0]), y - 1.5, "-o", c="C0")
    plt.axis("off")

    alignment_plot_path_png = os.path.join(output_folder, f"DTW_Alignment_{file_suffix}.png")
    alignment_plot_path_svg = os.path.join(output_folder, f"DTW_Alignment_{file_suffix}.svg")
    plt.savefig(alignment_plot_path_png, dpi=300)
    plt.savefig(alignment_plot_path_svg, format='svg')
    plt.close()

    return dist_cost_plot_path, alignment_plot_path_png

def normalize_sequence(seq):
    """
    Normalize the sequence to a range of [0, 1] using min-max normalization.
    """
    min_val = np.min(seq)
    max_val = np.max(seq)
    return (seq - min_val) / (max_val - min_val) if max_val - min_val != 0 else seq  # Avoid division by zero

def calculate_dtw_cost_with_normalization(surrounding_values, surrounding_indices, integrated_areas_data, output_folder):
    dtw_costs = {}
    
    for i, indices in enumerate(surrounding_indices):
        dtw_costs[f'Discontinuity_{i+1}'] = {}
        
        adjusted_indices = indices + 1
        
        for peak in integrated_areas_data.columns:
            integrated_values = integrated_areas_data[peak].values[adjusted_indices]
            pca_values = surrounding_values[i]
            
            # Normalize both sequences before calculating DTW
            pca_values_normalized = normalize_sequence(pca_values)
            integrated_values_normalized = normalize_sequence(integrated_values)
            
            if len(pca_values_normalized) == len(integrated_values_normalized):  # Ensure lengths match
                # Create the distance matrix
                dist_mat = np.abs(np.subtract.outer(pca_values_normalized, integrated_values_normalized))
                
                # Compute DTW alignment cost
                path, cost_mat = dp(dist_mat)
                
                # Use non-normalized alignment cost (raw cost)
                dtw_cost = cost_mat[-1, -1]
                
                # Store the non-normalized DTW cost
                dtw_costs[f'Discontinuity_{i+1}'][peak] = dtw_cost

                # Plot the matrices and alignment path
                file_suffix = f"Disc_{i+1}_Peak_{peak.replace(' ', '_')}"
                plot_dtw_matrices_and_path(dist_mat, cost_mat, path, pca_values_normalized, integrated_values_normalized, output_folder, file_suffix)
    
    return dtw_costs

# Use this function in place of the original DTW cost calculation
output_folder = os.path.join(folder_path, 'DTW_Plots')
os.makedirs(output_folder, exist_ok=True)

dtw_results = calculate_dtw_cost_with_normalization(surrounding_values, surrounding_indices, integrated_areas_data, output_folder)

def prepare_dtw_matrix(dtw_results):
    discontinuities = list(dtw_results.keys())
    peaks = list(next(iter(dtw_results.values())).keys())
    
    matrix = np.zeros((len(discontinuities), len(peaks)))
    
    for i, disc in enumerate(discontinuities):
        for j, peak in enumerate(peaks):
            matrix[i, j] = dtw_results[disc][peak]
    
    return matrix, discontinuities, peaks

# Continue with the plotting and CSV saving logic as before

# Generate the DTW matrix
matrix, discontinuities, peaks = prepare_dtw_matrix(dtw_results)
discontinuity_times = [f"{time:.2f} s" for time in disc_times]

# Plot the DTW cost matrix as a heatmap
plt.figure(figsize=(14, 8))
ax = sns.heatmap(matrix, cmap=cmap, annot=True, cbar=True,
                 xticklabels=peaks, yticklabels=discontinuity_times,
                 linewidths=0.5, annot_kws={"size": 10},
                 cbar_kws={"shrink": 0.8, "ticks": [0, 50, 100, 150, 200]})

ax.set_xlabel('FTIR Peaks', fontsize=14, labelpad=20)
ax.set_ylabel('Discontinuities', fontsize=14, labelpad=10)
ax.set_title('Non-Normalized DTW Alignment Costs', fontsize=18, pad=20)

plt.xticks(rotation=45, ha='right', fontsize=10)
plt.yticks(fontsize=10)

plt.tight_layout()
plt.savefig(os.path.join(folder_path, 'DTW_Correlation_Matrix_Non_Normalized.png'), dpi=300)
plt.savefig(os.path.join(folder_path, 'DTW_Correlation_Matrix_Non_Normalized.svg'), format='svg')
plt.show()



metadata = {
    'SG Filter Window Length': [window_length],
    'SG Filter Polyorder': [polyorder],
    'Peak Threshold': [peak_threshold],
    'Trough Threshold': [trough_threshold],
    'Magnitude Threshold': [magnitude_threshold],
    'Average Discontinuity Magnitude': [avg_magnitude],
    'Standard Deviation of Discontinuity Magnitude': [std_magnitude]
}

discontinuity_info = pd.DataFrame({
    'Discontinuity Time (s)': discontinuity_times,
    'Discontinuity Magnitude': disc_magnitudes,
    'Discontinuity Value': disc_values
})

dtw_df = pd.DataFrame(dtw_results).T  # Transpose to have peaks as columns
dtw_df.index = discontinuity_times  # Use discontinuity times as row labels

dtw_averages = dtw_df.mean()
dtw_df.loc['Average'] = dtw_averages

csv_filename = os.path.join(folder_path, 'DTW_Analysis_Report.csv')

with open(csv_filename, 'w') as f:
    metadata_df = pd.DataFrame(metadata)
    metadata_df.to_csv(f, index=False)
    
    f.write("\n")  # Add some space between sections
    
    discontinuity_info.to_csv(f, index=False)
    
    f.write("\n")  # Add some space between sections
    
    dtw_df.to_csv(f, index_label='Discontinuity Time (s)')




