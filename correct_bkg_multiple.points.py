'''

Just run it. It will create a window where you select file and etc. If it doesn't work, try to reverse the order, by switching

    df = pd.read_csv(self.file_path, header=None, skiprows=1).iloc[:, :]#[::-1]

into 

    df = pd.read_csv(self.file_path, header=None, skiprows=1).iloc[:, :][::-1]

'''



import os
import pandas as pd
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class SpectraCorrectionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Spectra Background Correction")
        
        self.file_path = None
        self.background_points = []  # List to store selected points
        self.background_lines = []   # List to store the line objects for visualization
        self.spectra = None
        self.wavenumbers = None
        self.corrected_spectra = None
        
        self.setup_gui()
        
    def setup_gui(self):
        # Top frame for buttons
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=5, fill=tk.X)
        
        self.load_button = tk.Button(button_frame, text="Load Spectra", command=self.load_file)
        self.load_button.pack(side=tk.LEFT, padx=5)

        self.reset_button = tk.Button(button_frame, text="Reset Selection", command=self.reset_selection)
        self.reset_button.pack(side=tk.LEFT, padx=5)
        
        self.apply_button = tk.Button(button_frame, text="Apply Correction", command=self.apply_correction)
        self.apply_button.pack(side=tk.LEFT, padx=5)
        self.apply_button.config(state=tk.DISABLED)
        
        self.save_button = tk.Button(button_frame, text="Save Corrected Spectra", command=self.save_corrected_spectra)
        self.save_button.pack(side=tk.LEFT, padx=5)
        self.save_button.config(state=tk.DISABLED)

        # Status label
        self.status_var = tk.StringVar()
        self.status_var.set("Status: Ready to load file")
        self.status_label = tk.Label(self.root, textvariable=self.status_var, anchor='w')
        self.status_label.pack(pady=2, fill=tk.X, padx=5)

        # Points label
        self.points_var = tk.StringVar()
        self.points_var.set("Selected points: 0")
        self.points_label = tk.Label(self.root, textvariable=self.points_var, anchor='w')
        self.points_label.pack(pady=2, fill=tk.X, padx=5)

        # Plot area
        self.figure = Figure(figsize=(10, 6))
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, self.root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.canvas.mpl_connect("button_press_event", self.on_click)

    def load_file(self):
        self.file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not self.file_path:
            return
        
        self.load_spectra()
        self.plot_spectra()
        self.status_var.set(f"Status: Loaded file {os.path.basename(self.file_path)}")
        self.reset_selection()  # Reset any previous selection

    def load_spectra(self):
        try:
            df = pd.read_csv(self.file_path, header=None, skiprows=1).iloc[:, :]#[::-1]
            self.wavenumbers = df.iloc[:, 0].values
            self.spectra = df.iloc[:, 1:].to_numpy()  # Convert to NumPy array for efficiency
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {str(e)}")
            self.status_var.set("Status: Error loading file")

    def plot_spectra(self):
        self.ax.clear()
        if self.spectra is None:
            return
            
        for i in range(self.spectra.shape[1]):
            self.ax.plot(self.wavenumbers, self.spectra[:, i], label=f'Spectrum {i}')
        self.ax.set_xlabel("Wavenumber")
        self.ax.set_ylabel("Intensity")
        self.figure.tight_layout()
        self.canvas.draw()

    def on_click(self, event):
        if event.inaxes is not None and self.spectra is not None:
            # Add the new point to our list
            self.background_points.append(event.xdata)
            
            # Sort points in ascending order
            self.background_points.sort()
            
            # Update display
            self.update_points_display()
            
            # Enable apply button if we have at least 2 points
            if len(self.background_points) >= 2:
                self.apply_button.config(state=tk.NORMAL)

    def update_points_display(self):
        # Clear previous lines
        for line in self.background_lines:
            line.remove()
        self.background_lines = []
        
        # Draw new vertical lines for each point
        for point in self.background_points:
            line = self.ax.axvline(point, color='red', linestyle='--')
            self.background_lines.append(line)
        
        # Update points label
        self.points_var.set(f"Selected points: {len(self.background_points)}")
        
        # Redraw canvas
        self.canvas.draw()

    def apply_correction(self):
        """Perform piecewise linear background correction using all selected points."""
        if len(self.background_points) < 2:
            messagebox.showerror("Error", "Need at least 2 points for correction")
            return
            
        # Create copy of original spectra data
        self.corrected_spectra = np.copy(self.spectra)
        
        # Find indices of the wavenumbers closest to selected points
        point_indices = [np.abs(self.wavenumbers - point).argmin() for point in self.background_points]
        
        # Get background values at those points
        background_values = self.spectra[point_indices, :]
        
        # Perform piecewise linear correction between each consecutive pair of points
        for i in range(len(point_indices) - 1):
            start_idx = point_indices[i]
            end_idx = point_indices[i+1]
            
            # Skip if indices are the same (shouldn't happen with sorted points)
            if start_idx == end_idx:
                continue
                
            # Calculate section indices
            section_indices = np.arange(start_idx, end_idx + 1)
            
            # Get x values (wavenumbers) for this section
            x_section = self.wavenumbers[section_indices]
            
            # For each spectrum
            for spec_idx in range(self.spectra.shape[1]):
                # Get background values for this spectrum at the two points
                y_start = background_values[i, spec_idx]
                y_end = background_values[i+1, spec_idx]
                
                # Calculate slope and intercept for linear interpolation
                x_start = self.wavenumbers[start_idx]
                x_end = self.wavenumbers[end_idx]
                
                slope = (y_end - y_start) / (x_end - x_start)
                intercept = y_start - slope * x_start
                
                # Calculate background for this section
                background = slope * x_section + intercept
                
                # Apply correction to this section of this spectrum
                self.corrected_spectra[section_indices, spec_idx] -= background
        
        # Set boundary points to NaN to create gaps that will be interpolated
        for idx in point_indices:
            self.corrected_spectra[idx, :] = np.nan
        
        # Interpolate over the NaN values to connect adjacent points with straight lines
        for spec_idx in range(self.corrected_spectra.shape[1]):
            mask = np.isnan(self.corrected_spectra[:, spec_idx])
            if np.any(mask):
                # Get valid (non-NaN) indices
                valid_indices = np.where(~mask)[0]
                valid_values = self.corrected_spectra[valid_indices, spec_idx]
                
                # Interpolate over NaN values
                self.corrected_spectra[:, spec_idx] = np.interp(
                    np.arange(len(self.wavenumbers)),
                    valid_indices,
                    valid_values
                )
        
        # Plot corrected spectra
        self.plot_corrected_spectra()
        
        # Enable save button
        self.save_button.config(state=tk.NORMAL)
        
        # Update status
        self.status_var.set(f"Status: Correction applied using {len(self.background_points)} points")

    def plot_corrected_spectra(self):
        if self.corrected_spectra is None:
            return
            
        self.ax.clear()
        for i in range(self.corrected_spectra.shape[1]):
            self.ax.plot(self.wavenumbers, self.corrected_spectra[:, i], label=f'Corrected Spectrum {i}')
        
        # Re-draw the background points
        self.background_lines = []
        for point in self.background_points:
            line = self.ax.axvline(point, color='red', linestyle='--')
            self.background_lines.append(line)
            
        self.ax.set_xlabel("Wavenumber")
        self.ax.set_ylabel("Corrected Intensity")
        self.figure.tight_layout()
        self.canvas.draw()

    def save_corrected_spectra(self):
        if self.corrected_spectra is None:
            messagebox.showerror("Error", "No corrected spectra to save")
            return
            
        output_directory = os.path.join(os.path.dirname(self.file_path), "Corrected Spectra")
        os.makedirs(output_directory, exist_ok=True)
        
        corrected_df = pd.DataFrame(self.corrected_spectra, columns=[f"Spectrum_{i}" for i in range(self.corrected_spectra.shape[1])])
        corrected_df.insert(0, "Wavenumber", self.wavenumbers)
        
        output_file_path = os.path.join(output_directory, os.path.basename(self.file_path).replace(".csv", "_bkg_corrected.csv"))
        corrected_df.to_csv(output_file_path, index=False, header=False)
        messagebox.showinfo("Save Successful", f"Corrected spectra saved to {output_file_path}")
        self.status_var.set(f"Status: Saved to {os.path.basename(output_file_path)}")

    def reset_selection(self):
        """Resets the selection to allow a new background correction."""
        self.background_points = []
        self.background_lines = []
        self.corrected_spectra = None
        
        # Update display
        if self.spectra is not None:
            self.plot_spectra()
            
        # Update status
        self.status_var.set("Status: Selection reset")
        self.points_var.set("Selected points: 0")
        
        # Disable buttons
        self.apply_button.config(state=tk.DISABLED)
        self.save_button.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    app = SpectraCorrectionApp(root)
    root.geometry("800x600")  # Set initial window size
    root.mainloop()
