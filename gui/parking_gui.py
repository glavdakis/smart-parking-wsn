import tkinter as tk
from tkinter import ttk, messagebox, Canvas
import serial
import threading
import time
from datetime import datetime
from PIL import Image, ImageTk
import math
import os

# Manual COM port configuration
COM_PORT = "COM14"  # COM port

class ParkingArea:
    def __init__(self, name, x, y, color, pricing):
        self.name = name
        self.x = x
        self.y = y
        self.color = color
        self.capacity = 50
        self.occupied = 0
        self.available = 50
        self.cars_entered = 0
        self.cars_exited = 0
        self.pricing = pricing  


class ParkingGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Parking Management System")
        self.root.geometry("1400x900")  # Made window larger
        self.root.minsize(1200, 800)  # Set minimum size
        self.root.configure(bg='#2c3e50')

        # Arduino connection variables
        self.arduino = None
        self.is_connected = False
        self.serial_thread = None
        self.running = False

        # Map background image - LA image Google map
        self.map_image_path = os.path.join(os.path.dirname(__file__), "map.png")
        self.map_image_original = Image.open(self.map_image_path)
        self.map_image_tk = None  # Will hold the resized version for canvas
        self.map_bg_id = None  # Store the background image ID for updating

        # Initialize parking areas
        self.parking_areas = {
            "Mall Parking": ParkingArea("Mall Parking", 200, 150, "#3498db", {
                    "first_3h": 3, "next_per_hour": 2}),
            "Pasadena": ParkingArea("Pasadena", 500, 100, "#e74c3c", {
                    "first_3h": 4, "next_per_hour": 2.5}),
            "City Center": ParkingArea("City Center", 350, 300, "#27ae60", {
                    "first_3h": 2.5, "next_per_hour": 1.5}),
            "Airport Parking": ParkingArea("Airport Parking", 150, 400, "#f39c12", {
                    "first_3h": 5, "next_per_hour": 3.5}),
            "Suburban Area": ParkingArea("Suburban Area", 550, 350, "#9b59b6", {
                    "first_3h": 4.5, "next_per_hour": 3})
        }

        self.selected_area = None
        self.selected_area_name = None

        self.style = ttk.Style()
        self.style.theme_use('default')  # Ensure it works across platforms
        self.style.configure('Custom.Horizontal.TProgressbar', background='#3498db')

        self.setup_gui()

    def setup_gui(self):
        # Create main container with scrollable right panel
        main_container = tk.Frame(self.root, bg='#2c3e50')
        main_container.pack(fill='both', expand=True)

        # Left panel for map (60% of the width)
        map_frame = tk.Frame(main_container, bg='#34495e', relief='raised', bd=2)
        map_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)

        # Right panel for controls and info (fixed width with scrollbar)
        right_panel_container = tk.Frame(main_container, bg='#2c3e50', width=450)
        right_panel_container.pack(side='right', fill='y', padx=5, pady=5)
        right_panel_container.pack_propagate(False)

        # Create scrollable frame for the right panel
        self.setup_scrollable_control_panel(right_panel_container)

        self.setup_map_panel(map_frame)

    def setup_scrollable_control_panel(self, parent):
        # Create canvas and scrollbar for scrollable content
        canvas = Canvas(parent, bg='#2c3e50', highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#2c3e50')

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack the canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Setup the control panel content in the scrollable frame
        self.setup_control_panel(scrollable_frame)

    def setup_map_panel(self, parent):
        # Map title
        map_title = tk.Label(parent, text="🗺️ Downtown Parking Areas",
                             font=('Arial', 18, 'bold'),
                             fg='#ecf0f1', bg='#34495e')
        map_title.pack(pady=10)

        # Instructions
        instruction_label = tk.Label(parent, text="Click on a parking area to select and monitor it",
                                     font=('Arial', 12),
                                     fg='#bdc3c7', bg='#34495e')
        instruction_label.pack(pady=5)

        # Create canvas for map
        canvas_frame = tk.Frame(parent, bg='#34495e')
        canvas_frame.pack(fill='both', expand=True, padx=10, pady=10)

        self.map_canvas = Canvas(canvas_frame, bg='#2c3e50', highlightthickness=0)
        self.map_canvas.pack(fill='both', expand=True)

        # Bind canvas events
        self.map_canvas.bind("<Button-1>", self.on_map_click)
        self.map_canvas.bind("<Motion>", self.on_map_hover)
        self.map_canvas.bind("<Configure>", self.on_canvas_resize)

        # Legend
        legend_frame = tk.Frame(parent, bg='#34495e')
        legend_frame.pack(pady=5)

        tk.Label(legend_frame, text="Legend:", font=('Arial', 12, 'bold'),
                 fg='#ecf0f1', bg='#34495e').pack(anchor='w')

        legend_items = [
            #("🔵 Available Areas", "#3498db"),
            ("🟡 Selected Area", "#f1c40f"),
            ("🅿 Each parking area has 50 parking spots", "#ecf0f1")
        ]

        for text, color in legend_items:
            item_frame = tk.Frame(legend_frame, bg='#34495e')
            item_frame.pack(anchor='w')

            if color != "#ecf0f1":
                color_box = tk.Frame(item_frame, bg=color, width=15, height=15)
                color_box.pack(side='left', padx=5, pady=2)

            tk.Label(item_frame, text=text, font=('Arial', 10),
                     fg=color, bg='#34495e').pack(side='left', padx=5)

    def setup_control_panel(self, parent):
        # Main title
        title_label = tk.Label(parent, text="🚗 Smart Parking",
                               font=('Arial', 20, 'bold'),
                               fg='#ecf0f1', bg='#2c3e50')
        title_label.pack(pady=10)

        # Connection status
        status_frame = tk.Frame(parent, bg='#34495e', relief='raised', bd=2)
        status_frame.pack(pady=10, fill='x')

        self.connection_label = tk.Label(status_frame, text="● Disconnected",
                                         font=('Arial', 12),
                                         fg='#e74c3c', bg='#34495e')
        self.connection_label.pack(pady=5)

        # Arduino connection
        conn_frame = tk.Frame(parent, bg='#2c3e50')
        conn_frame.pack(pady=10, fill='x')

        tk.Label(conn_frame, text=f"COM Port: {COM_PORT}", font=('Arial', 10),
                 fg='#ecf0f1', bg='#2c3e50').pack(anchor='w')

        port_frame = tk.Frame(conn_frame, bg='#2c3e50')
        port_frame.pack(fill='x', pady=5)

        self.connect_btn = tk.Button(port_frame, text="Connect",
                                     command=self.connect_arduino,
                                     bg='#27ae60', fg='white',
                                     font=('Arial', 10), width=12)
        self.connect_btn.pack(side='left')

        self.disconnect_btn = tk.Button(port_frame, text="Disconnect",
                                        command=self.disconnect_arduino,
                                        bg='#e74c3c', fg='white',
                                        font=('Arial', 10), width=12,
                                        state='disabled')
        self.disconnect_btn.pack(side='left', padx=5)

        # Selected area info
        area_frame = tk.Frame(parent, bg='#34495e', relief='raised', bd=2)
        area_frame.pack(pady=10, fill='x')

        tk.Label(area_frame, text="Selected Parking Area",
                 font=('Arial', 14, 'bold'), fg='#ecf0f1', bg='#34495e').pack(pady=5)

        self.area_name_label = tk.Label(area_frame, text="No area selected",
                                        font=('Arial', 12, 'bold'), fg='#f1c40f', bg='#34495e')
        self.area_name_label.pack(pady=2)

        self.area_info_label = tk.Label(area_frame, text="Select an area from the map",
                                        font=('Arial', 10), fg='#bdc3c7', bg='#34495e',
                                        wraplength=400)
        self.area_info_label.pack(pady=2)

        self.pricing_info_label = tk.Label(area_frame, text="",
                                   font=('Arial', 10), fg='#bdc3c7', bg='#34495e',
                                   wraplength=400)
        self.pricing_info_label.pack(pady=2)

        # Statistics for selected area
        stats_frame = tk.Frame(parent, bg='#34495e', relief='raised', bd=2)
        stats_frame.pack(pady=10, fill='x')

        tk.Label(stats_frame, text="Area Statistics",
                 font=('Arial', 14, 'bold'), fg='#ecf0f1', bg='#34495e').pack(pady=5)

        # Large display cards - made more compact
        cards_container = tk.Frame(stats_frame, bg='#34495e')
        cards_container.pack(pady=5)

        # Capacity card
        capacity_card = tk.Frame(cards_container, bg='#3498db', relief='raised', bd=2)
        capacity_card.pack(pady=2, fill='x')

        tk.Label(capacity_card, text="CAPACITY", font=('Arial', 9, 'bold'),
                 fg='white', bg='#3498db').pack()
        self.capacity_display = tk.Label(capacity_card, text="50",
                                         font=('Arial', 20, 'bold'), fg='white', bg='#3498db')
        self.capacity_display.pack()

        # Occupied card
        occupied_card = tk.Frame(cards_container, bg='#e74c3c', relief='raised', bd=2)
        occupied_card.pack(pady=2, fill='x')

        tk.Label(occupied_card, text="OCCUPIED", font=('Arial', 9, 'bold'),
                 fg='white', bg='#e74c3c').pack()
        self.occupied_display = tk.Label(occupied_card, text="0",
                                         font=('Arial', 20, 'bold'), fg='white', bg='#e74c3c')
        self.occupied_display.pack()

        # Available card
        available_card = tk.Frame(cards_container, bg='#27ae60', relief='raised', bd=2)
        available_card.pack(pady=2, fill='x')

        tk.Label(available_card, text="AVAILABLE", font=('Arial', 9, 'bold'),
                 fg='white', bg='#27ae60').pack()
        self.available_display = tk.Label(available_card, text="50",
                                          font=('Arial', 20, 'bold'), fg='white', bg='#27ae60')
        self.available_display.pack()

        # Progress bar
        progress_frame = tk.Frame(stats_frame, bg='#34495e')
        progress_frame.pack(pady=10)

        tk.Label(progress_frame, text="Occupancy Level", font=('Arial', 11, 'bold'),
                 fg='#ecf0f1', bg='#34495e').pack()

        self.occupancy_progress = ttk.Progressbar(progress_frame, length=350, mode='determinate')
        self.occupancy_progress.pack(pady=5)

        self.occupancy_label = tk.Label(progress_frame, text="0%",
                                        font=('Arial', 12, 'bold'), fg='#ecf0f1', bg='#34495e')
        self.occupancy_label.pack()

        # Manual controls - made more prominent
        control_section = tk.Frame(parent, bg='#34495e', relief='raised', bd=2)
        control_section.pack(pady=10, fill='x')

        tk.Label(control_section, text="🎮 Manual Controls",
                 font=('Arial', 14, 'bold'), fg='#ecf0f1', bg='#34495e').pack(pady=5)

        tk.Label(control_section, text="(Affects selected area only)",
                 font=('Arial', 9), fg='#bdc3c7', bg='#34495e').pack()

        btn_frame = tk.Frame(control_section, bg='#34495e')
        btn_frame.pack(pady=10)

        self.enter_btn = tk.Button(btn_frame, text="🚗 Car Enter (+1)",
                                   command=self.manual_car_enter,
                                   bg='#e74c3c', fg='white', font=('Arial', 11, 'bold'),
                                   width=18, height=2,
                                   state='disabled')
        self.enter_btn.pack(pady=3)

        self.exit_btn = tk.Button(btn_frame, text="🚙 Car Exit (-1)",
                                  command=self.manual_car_exit,
                                  bg='#27ae60', fg='white', font=('Arial', 11, 'bold'),
                                  width=18, height=2,
                                  state='disabled')
        self.exit_btn.pack(pady=3)

        self.reset_btn = tk.Button(btn_frame, text="🔄 Reset Area",
                                   command=self.reset_selected_area,
                                   bg='#f39c12', fg='white', font=('Arial', 11, 'bold'),
                                   width=18, height=2,
                                   state='disabled')
        self.reset_btn.pack(pady=3)

        tk.Button(btn_frame, text="🔄 Reset All Areas",
                  command=self.reset_all_areas,
                  bg='#8e44ad', fg='white', font=('Arial', 11, 'bold'),
                  width=18, height=2).pack(pady=3)

        # Activity log - made more prominent
        log_frame = tk.Frame(parent, bg='#34495e', relief='raised', bd=2)
        log_frame.pack(pady=10, fill='x')

        tk.Label(log_frame, text="📋 Activity Log",
                 font=('Arial', 14, 'bold'), fg='#ecf0f1', bg='#34495e').pack(pady=5)

        log_container = tk.Frame(log_frame, bg='#34495e')
        log_container.pack(fill='x', padx=5, pady=5)

        # Make log text area larger and more visible
        self.log_text = tk.Text(log_container, height=12, width=50, bg='#2c3e50', fg='#ecf0f1',
                                font=('Courier', 9), state='disabled', wrap='word')
        log_scrollbar = tk.Scrollbar(log_container, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=log_scrollbar.set)

        self.log_text.pack(side='left', fill='x', expand=True)
        log_scrollbar.pack(side='right', fill='y')

        # Clear log button
        clear_log_btn = tk.Button(log_frame, text="Clear Log",
                                  command=self.clear_log,
                                  bg='#95a5a6', fg='white', font=('Arial', 9))
        clear_log_btn.pack(pady=5)

        # Add some padding at the bottom for scrolling
        tk.Frame(parent, height=50, bg='#2c3e50').pack()

        # Initial log
        self.add_log("System initialized")
        self.add_log("Select a parking area from the map to start monitoring")

    def clear_log(self):
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, 'end')
        self.log_text.config(state='disabled')
        self.add_log("Log cleared")

    def draw_map(self):
        '''
        self.map_canvas.delete("all")
        canvas_width = self.map_canvas.winfo_width()
        canvas_height = self.map_canvas.winfo_height()

        if canvas_width <= 1:  # Canvas not ready
            return

        # Draw background elements (roads, buildings)
        self.draw_background(canvas_width, canvas_height)
        '''
        self.map_canvas.delete("all")
        canvas_width = self.map_canvas.winfo_width()
        canvas_height = self.map_canvas.winfo_height()

        if canvas_width <= 1:
            return

        # Resize and draw background image
        resized_image = self.map_image_original.resize((canvas_width, canvas_height))
        self.map_image_tk = ImageTk.PhotoImage(resized_image)
        self.map_bg_id = self.map_canvas.create_image(0, 0, image=self.map_image_tk, anchor='nw')
        # Draw parking areas
        for area_name, area in self.parking_areas.items():
            x, y = area.x, area.y

            # Determine color - yellow if selected, original color if not
            if self.selected_area_name == area_name:
                fill_color = "#f1c40f"
                outline_color = "#f39c12"
                outline_width = 3
            else:
                fill_color = area.color
                outline_color = "black"
                outline_width = 2

            # Draw smaller area rectangle (represents the parking lot)
            radius1 = 20
            radius2 = 50
            area_rect = self.map_canvas.create_oval(
                x - radius2, y - radius1, x + radius2, y + radius1,
                fill=fill_color, outline=outline_color, width=outline_width
            )
            
            # Area name only (removed capacity, occupied, available info)
            self.map_canvas.create_text(x, y, text=area.name,
                                        fill="black", font=('Arial', 9, 'bold'))

            # Store rectangle ID for click detection
            area.rect_id = area_rect

    def draw_background(self, width, height):
        # Draw roads
        # Horizontal road
        self.map_canvas.create_rectangle(0, height // 2 - 20, width, height // 2 + 20,
                                         fill="#34495e", outline="#2c3e50", width=2)

        # Vertical road
        self.map_canvas.create_rectangle(width // 2 - 20, 0, width // 2 + 20, height,
                                         fill="#34495e", outline="#2c3e50", width=2)

        # Road markings
        for i in range(0, width, 40):
            self.map_canvas.create_rectangle(i, height // 2 - 2, i + 20, height // 2 + 2,
                                             fill="#f1c40f", outline="")

        for i in range(0, height, 40):
            self.map_canvas.create_rectangle(width // 2 - 2, i, width // 2 + 2, i + 20,
                                             fill="#f1c40f", outline="")

        # Draw some buildings (smaller buildings)
        buildings = [
            (100, 80, 130, 110, "#7f8c8d"),  # Building 1
            (450, 50, 480, 80, "#7f8c8d"),  # Building 2
            (600, 250, 630, 280, "#7f8c8d"),  # Building 3
            (80, 350, 110, 380, "#7f8c8d"),  # Building 4
            (250, 480, 280, 510, "#7f8c8d"),  # Building 5
        ]

        for x1, y1, x2, y2, color in buildings:
            self.map_canvas.create_rectangle(x1, y1, x2, y2,
                                             fill=color, outline="#95a5a6", width=1)
            # Add building label
            center_x, center_y = (x1 + x2) // 2, (y1 + y2) // 2
            self.map_canvas.create_text(center_x, center_y, text="🏢",
                                        fill="white", font=('Arial', 12))

    def on_canvas_resize(self, event):                         
        self.root.after(100, self.draw_map)

    def on_map_click(self, event):
        # Get the click position
        click_x, click_y = event.x, event.y

        clicked_on_area = False

        # Check if user clicked inside any parking area
        for area_name, area in self.parking_areas.items():
            if (area.x - 50 <= click_x <= area.x + 50 and
                area.y - 35 <= click_y <= area.y + 35):               
               self.select_area(area_name)
               clicked_on_area = True
               break
        
        # If user clicked outside all areas, deselect
        if not clicked_on_area:
            self.selected_area = None
            self.selected_area_name = None

            # Update UI to reflect no selection
            self.area_name_label.config(text="No area selected")
            self.area_info_label.config(text="Select an area from the map")
        
            self.enter_btn.config(state='disabled')
            self.exit_btn.config(state='disabled')
            self.reset_btn.config(state='disabled')

            self.update_display()
            self.add_log("Deselected parking area")

            self.pricing_info_label.config(text="")

    def on_map_hover(self, event):
        # Could add hover effects here
        pass

    def select_area(self, area_name):
        self.selected_area_name = area_name
        self.selected_area = self.parking_areas[area_name]

        # Update area info display
        self.area_name_label.config(text=self.selected_area.name)
        self.area_info_label.config(text=f"Monitoring this area") 

        pricing = self.selected_area.pricing
        self.pricing_info_label.config(
            text=f"Pricing: First 3 hours = {pricing['first_3h']}€, then {pricing['next_per_hour']}€/hour"
        )

        # Enable manual control buttons
        self.enter_btn.config(state='normal')
        self.exit_btn.config(state='normal')
        self.reset_btn.config(state='normal')

        # Update display
        self.update_display()
        self.draw_map()

        self.add_log(f"Selected {area_name} for monitoring")
        self.add_log(f"Arduino commands will now affect {area_name}")

    def connect_arduino(self):
        try:
            self.arduino = serial.Serial(COM_PORT, 9600, timeout=1)
            time.sleep(2)
            self.is_connected = True
            self.running = True

            self.serial_thread = threading.Thread(target=self.read_arduino_data, daemon=True)
            self.serial_thread.start()

            self.connection_label.config(text="● Connected", fg='#27ae60')
            self.connect_btn.config(state='disabled')
            self.disconnect_btn.config(state='normal')
            self.add_log(f"Connected to Arduino on {COM_PORT}")

            if self.selected_area:
                self.add_log(f"Arduino data will affect {self.selected_area.name}")
            else:
                self.add_log("Select a parking area to receive Arduino data")

        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect to {COM_PORT}: {str(e)}")
            self.add_log(f"Connection failed: {str(e)}")

    def disconnect_arduino(self):
        self.running = False
        self.is_connected = False

        if self.arduino:
            self.arduino.close()
            self.arduino = None

        self.connection_label.config(text="● Disconnected", fg='#e74c3c')
        self.connect_btn.config(state='normal')
        self.disconnect_btn.config(state='disabled')
        self.add_log("Disconnected from Arduino")

    def read_arduino_data(self):
        while self.running and self.arduino:
            try:
                if self.arduino.in_waiting > 0:
                    data = self.arduino.readline().decode('utf-8').strip()
                    if data:
                        self.process_arduino_data(data)
                time.sleep(0.1)
            except Exception as e:
                self.add_log(f"Error reading data: {str(e)}")
                break

    def process_arduino_data(self, data):
        if not self.selected_area:
            self.add_log(f"Arduino data received but no area selected: {data}")
            return

        # Expected format: "ENTER" or "EXIT"
        if data == "ENTER":
            self.car_entered()
        elif data == "EXIT":
            self.car_exited()
        else:
            self.add_log(f"Unknown Arduino command: {data}")

    def car_entered(self):
        if not self.selected_area:
            self.add_log("No area selected - cannot process car entry")
            return

        if self.selected_area.occupied < self.selected_area.capacity:
            self.selected_area.occupied += 1
            self.selected_area.cars_entered += 1
            self.selected_area.available = self.selected_area.capacity - self.selected_area.occupied
            self.update_display()
            self.add_log(f"Car entered {self.selected_area.name}")
        else:
            self.add_log(f"{self.selected_area.name} is full - car cannot enter")

    def car_exited(self):
        if not self.selected_area:
            self.add_log("No area selected - cannot process car exit")
            return

        if self.selected_area.occupied > 0:
            self.selected_area.occupied -= 1
            self.selected_area.cars_exited += 1
            self.selected_area.available = self.selected_area.capacity - self.selected_area.occupied
            self.update_display()
            self.add_log(f"Car exited from {self.selected_area.name}")
        else:
            self.add_log(f"No cars in {self.selected_area.name} to exit")

    def manual_car_enter(self):
        self.car_entered()

    def manual_car_exit(self):
        self.car_exited()

    def reset_selected_area(self):
        if not self.selected_area:
            return

        self.selected_area.occupied = 0
        self.selected_area.available = self.selected_area.capacity
        self.selected_area.cars_entered = 0
        self.selected_area.cars_exited = 0

        self.update_display()
        self.add_log(f"Reset {self.selected_area.name} - all counters cleared")

    def reset_all_areas(self):
        for area in self.parking_areas.values():
            area.occupied = 0
            area.available = area.capacity
            area.cars_entered = 0
            area.cars_exited = 0

        self.update_display()
        self.add_log("Reset all parking areas - all counters cleared")

    def update_display(self):
        if not self.selected_area:
            # Show default values when no area is selected
            self.capacity_display.config(text="--")
            self.occupied_display.config(text="--")
            self.available_display.config(text="--")
            self.occupancy_progress['value'] = 0
            self.occupancy_label.config(text="No area selected")
        else:
            # Update display with selected area data
            area = self.selected_area

            self.capacity_display.config(text=str(area.capacity))
            self.occupied_display.config(text=str(area.occupied))
            self.available_display.config(text=str(area.available))

            # Update progress bar
            occupancy_percentage = (area.occupied / area.capacity) * 100
            self.occupancy_progress['value'] = occupancy_percentage
            self.occupancy_label.config(text=f"{occupancy_percentage:.1f}%")

            # Change progress bar color based on occupancy
            if occupancy_percentage <= 50:
                self.style.configure('Custom.Horizontal.TProgressbar', background='#3498db')  # Blue
            elif occupancy_percentage <= 75:
                self.style.configure('Custom.Horizontal.TProgressbar', background='#f39c12')  # Orange
            else:
                self.style.configure('Custom.Horizontal.TProgressbar', background='#c0392b')  # Red

            self.occupancy_progress.configure(style='Custom.Horizontal.TProgressbar')

            # Notification if full
            if area.occupied >= area.capacity:
                messagebox.showerror("Parking Full",
                                 f"{area.name} is FULL. No more cars can enter!")

        # Redraw map to reflect changes
        self.draw_map()

    def add_log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"

        self.log_text.config(state='normal')
        self.log_text.insert('end', log_entry)
        self.log_text.see('end')
        self.log_text.config(state='disabled')


def main():
    root = tk.Tk()

    # Configure ttk styles
    style = ttk.Style()
    style.configure('TProgressbar', background='#3498db')

    app = ParkingGUI(root)

    def on_closing():
        app.disconnect_arduino()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    # Initial map drawing after a short delay
    root.after(500, app.draw_map)

    root.mainloop()


if __name__ == "__main__":
    main()