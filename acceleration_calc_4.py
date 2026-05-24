import streamlit as st
import pandas as pd
import math

# --- 1. THE PHYSICS ENGINE ---
def simulate_run(mass, peak_torque, redline, class_choice, t_width, t_aspect, t_rim):
    sidewall_mm = t_width * (t_aspect / 100.0)
    rim_radius_mm = (t_rim * 25.4) / 2.0
    tire_radius = (sidewall_mm + rim_radius_mm) / 1000.0
    
    if "Sports" in class_choice:
        GEAR_RATIOS = {1: 3.10, 2: 2.15, 3: 1.55, 4: 1.20, 5: 1.00, 6: 0.80}
        FINAL_DRIVE = 4.10
    elif "Truck" in class_choice:
        GEAR_RATIOS = {1: 4.50, 2: 2.60, 3: 1.50, 4: 1.00, 5: 0.75}
        FINAL_DRIVE = 4.10
    else:
        GEAR_RATIOS = {1: 3.50, 2: 2.00, 3: 1.30, 4: 0.95, 5: 0.75}
        FINAL_DRIVE = 3.80

    max_gears = len(GEAR_RATIOS)
    SHIFT_DELAY = 0.25                  
    
    # --- UPDATED FINAL CONSTANTS ---
    DRIVETRAIN_EFFICIENCY = 0.86        
    ROTATIONAL_INERTIA_FACTOR = 1.06    
    DRAG_COEFFICIENT = 0.32             
    
    effective_mass = mass * ROTATIONAL_INERTIA_FACTOR
    max_traction = 0.8 * mass * 9.81
    
    def get_torque(rpm):
        idle = 1000
        rpm_range = max(1000, redline - idle)
        curve = [
            (idle, 0.70), (idle + (0.2 * rpm_range), 0.83),
            (idle + (0.45 * rpm_range), 1.00), (idle + (0.65 * rpm_range), 0.98),
            (idle + (0.85 * rpm_range), 0.87), (redline, 0.72)
        ]
        if rpm <= curve[0][0]: return curve[0][1] * peak_torque
        if rpm >= curve[-1][0]: return curve[-1][1] * peak_torque
        for i in range(len(curve) - 1):
            if curve[i][0] <= rpm <= curve[i+1][0]:
                frac = (rpm - curve[i][0]) / (curve[i+1][0] - curve[i][0])
                return (curve[i][1] + frac * (curve[i+1][1] - curve[i][1])) * peak_torque
        return peak_torque

    time = 0.0
    velocity = 0.001                    
    current_gear = 1
    shift_timer = 0.0
    time_step = 0.01
    
    time_log, speed_log, rpm_log, torque_log = [time], [0.0], [1000], [0.0]

    while velocity < (100 / 3.6) and time < 30.0:
        wheel_rpm = (velocity * 60) / (2 * math.pi * tire_radius)
        engine_rpm = max(1000, wheel_rpm * GEAR_RATIOS[current_gear] * FINAL_DRIVE)

        if engine_rpm >= redline and current_gear < max_gears and shift_timer <= 0:
            current_gear += 1
            shift_timer = SHIFT_DELAY

        if shift_timer > 0:
            engine_torque = 0.0
            active_thrust = 0.0
            shift_timer -= time_step
            engine_rpm = 1000
        else:
            engine_torque = get_torque(engine_rpm)
            raw_thrust = (engine_torque * GEAR_RATIOS[current_gear] * FINAL_DRIVE * DRIVETRAIN_EFFICIENCY) / tire_radius
            active_thrust = min(raw_thrust, max_traction)

        # Environmental Resistance Calculations
        drag = 0.5 * 1.225 * (velocity ** 2) * DRAG_COEFFICIENT * 2.2
        rolling_res = 0.015 * mass * 9.81
        
        # --- UPDATED: Allow negative acceleration for shift deceleration ---
        net_force = active_thrust - drag - rolling_res
        accel = net_force / effective_mass
        
        velocity += accel * time_step
        
        # Prevent the car from rolling backward off the line
        if velocity < 0.001:
            velocity = 0.001 
            
        time += time_step
        
        time_log.append(time)
        speed_log.append(velocity * 3.6)
        rpm_log.append(engine_rpm)
        torque_log.append(engine_torque)

    return time, current_gear, tire_radius, time_log, speed_log, rpm_log, torque_log


# --- 2. INTERFACE DESIGN ---
st.set_page_config(page_title="Vehicle 0-100 Simulator", layout="wide")

st.title("🏁 Vehicle 0-100 km/h Simulator")
st.markdown("Adjust specifications in the left sidebar, then click run.")

# Sidebar Configuration Controls
st.sidebar.header("⚙️ Engine & Chassis")
ui_mass = st.sidebar.number_input("Vehicle Mass (kg)", min_value=500.0, max_value=5000.0, value=1400.0, step=50.0)
ui_torque = st.sidebar.number_input("Peak Torque (Nm)", min_value=50.0, max_value=2000.0, value=230.0, step=10.0)
ui_redline = st.sidebar.slider("Engine Redline (RPM)", min_value=4000, max_value=9000, value=6500, step=100)

ui_class = st.sidebar.selectbox("Select Gearbox Type", ("Family Sedan (5-Speed)", "Sports Car (6-Speed)", "Heavy Truck (5-Speed)"))

st.sidebar.header("🛞 Tire Size Profile")
ui_width = st.sidebar.number_input("Width (mm)", value=225)
ui_aspect = st.sidebar.number_input("Aspect Ratio (%)", value=45)
ui_rim = st.sidebar.number_input("Rim Diameter (inches)", value=17)

# Execution Button
if st.button("🚀 RUN ACCELERATION SIMULATION", use_container_width=True):
    t_final, gear_final, r_tire, t_log, s_log, r_log, torq_log = simulate_run(
        ui_mass, ui_torque, ui_redline, ui_class, ui_width, ui_aspect, ui_rim
    )
    
    st.divider()
    
    # Display Summary Performance Cards
    c1, c2, c3 = st.columns(3)
    c1.metric("0-100 km/h Time", f"{t_final:.2f} seconds")
    c2.metric("Ending Gear", f"Gear {gear_final}")
    c3.metric("Calculated Wheel Radius", f"{r_tire:.3f} meters")
    
    # Bundle data cleanly into a standard Dataframe
    df = pd.DataFrame({
        'Speed': s_log,
        'RPM': r_log,
        'Torque': torq_log
    }, index=t_log)
    
    # Clean, responsive native charts
    st.subheader("📈 Acceleration Graph (km/h over Time)")
    st.line_chart(df['Speed'], color="#1f77b4")
    
    # Split engine performance into layout columns to bypass twin-axis limitations
    graph_col1, graph_col2 = st.columns(2)
    
    with graph_col1:
        st.subheader("⚙️ Engine Speed (RPM)")
        st.line_chart(df['RPM'], color="#ff7f0e")
        
    with graph_col2:
        st.subheader("🔧 Engine Output (Torque)")
        st.line_chart(df['Torque'], color="#2ca02c")
