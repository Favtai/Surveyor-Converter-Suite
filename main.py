import os
from nicegui import ui, app
import folium
import pandas as pd
import io
import converter_functions as converters
from nicegui import __version__ as nicegui_version

# ==========================================
# 1. SETUP & UTILS
# ==========================================
# Try to get EPSG codes, but provide a safe fallback if PyProj db is missing
try:
    EPSG_DICT = converters.get_epsg_codes()
except:
    EPSG_DICT = {}

EPSG_KEYS = list(EPSG_DICT.keys())
DEFAULT_SRC = EPSG_KEYS[0]
DEFAULT_TGT = EPSG_KEYS[1] if len(EPSG_KEYS) > 1 else EPSG_KEYS[0]

def update_map_html(lat, lon):
    """Generates the HTML string for the Leaflet map."""
    try:
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return "<div class='p-4 bg-red-100 text-red-800 rounded'>Invalid Coordinates for Map</div>"
        
        m = folium.Map(location=[lat, lon], zoom_start=7, tiles="CartoDB positron")
        folium.Marker([lat, lon], popup="Location", icon=folium.Icon(color="blue")).add_to(m)
        return m._repr_html_()
    except Exception as e:
        return f"<div class='p-4 bg-gray-100 text-gray-500 rounded'>Map Error: {str(e)}</div>"

async def get_upload_content(e):
    """Robustly retrieves file content across different NiceGUI versions."""
    # 1. Try modern .file attribute (NiceGUI 3.0+)
    if hasattr(e, 'file'):
        return await e.file.read()
    
    # 2. Try older .content attribute
    if hasattr(e, 'content'):
        return e.content.read()
    
    # 3. Try older .files attribute (lists of dicts)
    if hasattr(e, 'files') and e.files:
        return e.files[0]['content']
        
    raise AttributeError("Could not read upload. Please run: pip install nicegui --upgrade")

# ==========================================
# 2. UI HELPERS
# ==========================================
def section_header(text):
    ui.label(text).classes('text-lg font-bold text-slate-700 mb-2 mt-4')

def result_box(label_text="Result"):
    with ui.card().classes('w-full bg-slate-50 border border-slate-200 shadow-sm p-4 mt-4 items-center'):
        ui.label(label_text).classes('text-sm text-slate-500 uppercase tracking-wide')
        lbl = ui.label('-').classes('text-2xl font-mono text-blue-700 font-bold')
    return lbl

# ==========================================
# 3. ROBUST BATCH UI GENERATOR
# ==========================================
def create_batch_section(input_cols_needed=1, process_callback=None, **kwargs):
    state = {'df': None}
    
    with ui.card().classes('w-full p-6 bg-white shadow-md rounded-xl'):
        ui.markdown("### Upload CSV")
        
        uploader = ui.upload(label="Upload CSV", auto_upload=True).classes('w-full')
        
        # Selector Container
        selector_container = ui.row().classes('w-full gap-4 mt-4 hidden')
        sel_1 = ui.select([], label='Column 1')
        sel_2 = ui.select([], label='Column 2')
        
        if input_cols_needed == 2:
            sel_1.classes('w-1/2')
            sel_2.classes('w-1/2')
        else:
            sel_1.classes('w-full')
        
        with selector_container:
            if input_cols_needed == 1:
                sel_1.move(selector_container)
            else:
                sel_1.classes('w-1/2').props('label="Select X / Lon"')
                sel_2.move(selector_container)
                sel_1.move(selector_container)

        convert_btn = ui.button('Convert Column(s)', icon='play_arrow').classes('w-full bg-green-600 text-white mt-4 hidden')
        grid = ui.aggrid({'columnDefs': [], 'rowData': []}).classes('w-full h-64 hidden mt-4')
        
        def clear_batch():
            state['df'] = None
            selector_container.classes(add='hidden')
            convert_btn.classes(add='hidden')
            grid.classes(add='hidden')
            grid.options = {'columnDefs': [], 'rowData': []}
            grid.update()
            ui.notify('Cleared', type='info')
        
        ui.button('Clear & Reset', icon='clear', on_click=clear_batch).classes('w-full bg-red-600 text-white mt-4')

        async def on_upload(e):
            try:
                # USE THE SAFE HELPER
                file_bytes = await get_upload_content(e)
                
                state['df'] = pd.read_csv(io.BytesIO(file_bytes))
                cols = state['df'].columns.tolist()
                
                if not cols:
                    ui.notify("CSV has no columns!", type='warning'); return

                sel_1.options = cols; sel_1.value = cols[0]; sel_1.update()
                if input_cols_needed == 2:
                    sel_2.options = cols; sel_2.update()

                selector_container.classes(remove='hidden')
                convert_btn.classes(remove='hidden')
                ui.notify('CSV Loaded!', type='positive')
                
            except Exception as err:
                ui.notify(f"Upload/Read Error: {err}", type='negative')

        def on_convert():
            if state['df'] is None: return
            
            selected_cols = []
            if input_cols_needed == 1:
                if not sel_1.value: ui.notify("Select a column", type='warning'); return
                selected_cols = [sel_1.value]
            else:
                if not sel_1.value or not sel_2.value: ui.notify("Select both columns", type='warning'); return
                selected_cols = [sel_1.value, sel_2.value]

            try:
                runtime_kwargs = {k: v.value for k, v in kwargs.items()}
                result_df = process_callback(state['df'].copy(), selected_cols, **runtime_kwargs)
                
                grid.options['columnDefs'] = [{'field': c} for c in result_df.columns]
                grid.options['rowData'] = result_df.head(100).to_dict('records')
                grid.classes(remove='hidden')
                grid.update()
                
                buf = io.StringIO()
                result_df.to_csv(buf, index=False)
                ui.download(buf.getvalue().encode(), 'results.csv')
                ui.notify('Converted! Downloading...', type='positive')
            except Exception as err:
                ui.notify(f"Conversion Logic Error: {err}", type='negative')

        uploader.on_upload(on_upload)
        convert_btn.on_click(on_convert)


# ==========================================
# 4. MAIN LAYOUT
# ==========================================
with ui.header().classes('bg-slate-900 text-white items-center h-16 shadow-lg'):
    ui.icon('public', size='md').classes('ml-4 text-blue-400')
    ui.label('Surveyor Suite').classes('text-2xl font-bold ml-2')
    ui.label('v2.1').classes('text-xs bg-blue-600 px-2 py-1 rounded ml-4')

with ui.column().classes('w-full max-w-5xl mx-auto p-4 gap-6'):
    
    with ui.tabs().classes('w-full bg-white shadow-sm rounded-t-xl text-slate-600') as tabs:
        t_angle = ui.tab('Angle Tools', icon='architecture')
        t_dist = ui.tab('Distance', icon='straighten')
        t_coord = ui.tab('Coordinates', icon='place')
        t_area = ui.tab('Area', icon='square_foot')

    with ui.tab_panels(tabs, value=t_angle).classes('w-full bg-transparent p-0'):

        # --- TAB A: ANGLE TOOLS ---
        with ui.tab_panel(t_angle):
            with ui.grid(columns=2).classes('w-full gap-6'):
                # DD to DMS Section
                with ui.column().classes('w-full'):
                    ui.label('Decimal Degrees to DMS').classes('text-lg font-semibold mb-2')
                    mode_dd = ui.toggle(['Single', 'Batch'], value='Single').classes('w-full border-2 border-slate-200 rounded-lg p-1 bg-white mb-4')
                    
                    with ui.column().bind_visibility_from(mode_dd, 'value', value='Single').classes('w-full'):
                        with ui.card().classes('w-full p-6 bg-white shadow-md rounded-xl'):
                            with ui.row().classes('w-full items-end gap-4'):
                                val = ui.number(label='Decimal Degrees', value=0.0, format='%.6f').classes('w-1/3')
                                res = result_box("DMS Result")
                                
                                def reset_dd():
                                    val.value = 0.0
                                    res.set_text("DMS Result")
                                
                                with ui.row().classes('w-full gap-2 mt-4'):
                                    ui.button('Convert', icon='transform', on_click=lambda: res.set_text(converters.dd_to_dms_string(val.value))).classes('flex-grow bg-blue-600 text-white h-12')
                                    ui.button('Reset', icon='refresh', on_click=reset_dd).classes('bg-gray-600 text-white h-12')
                    
                    with ui.column().bind_visibility_from(mode_dd, 'value', value='Batch').classes('w-full'):
                        def proc_dd(df, cols, **kwargs):
                            df[f'{cols[0]}_DMS'] = df[cols[0]].apply(lambda x: converters.dd_to_dms_string(float(x)))
                            return df
                        create_batch_section(input_cols_needed=1, process_callback=proc_dd)
                
                # Azimuth & Bearings Section
                with ui.column().classes('w-full'):
                    ui.label('Azimuth & Bearings').classes('text-lg font-semibold mb-2')
                    mode_bear = ui.toggle(['Single', 'Batch'], value='Single').classes('w-full border-2 border-slate-200 rounded-lg p-1 bg-white mb-4')
                    
                    with ui.column().bind_visibility_from(mode_bear, 'value', value='Single').classes('w-full'):
                        with ui.card().classes('w-full p-6 bg-white shadow-md rounded-xl'):
                            with ui.tabs().classes('w-full text-slate-500') as az_tabs:
                                at_az_bear = ui.tab('Azimuth → Bearing')
                                at_bear_az = ui.tab('Bearing → Azimuth')
                            with ui.tab_panels(az_tabs, value=at_az_bear).classes('w-full'):
                                with ui.tab_panel(at_az_bear):
                                    with ui.row().classes('w-full items-center gap-4'):
                                        az_in = ui.number(label='Azimuth (0-360)', min=0, max=360, value=0).classes('w-1/3')
                                        az_res = ui.label('-').classes('text-xl font-mono font-bold text-blue-700 ml-4')
                                        
                                        def reset_az():
                                            az_in.value = 0
                                            az_res.set_text('-')
                                        
                                        with ui.row().classes('w-full gap-2 mt-4'):
                                            ui.button('Convert', icon='transform', on_click=lambda: az_res.set_text(converters.azimuth_to_bearing(az_in.value))).classes('flex-grow bg-slate-700 text-white h-12')
                                            ui.button('Reset', icon='refresh', on_click=reset_az).classes('bg-gray-600 text-white h-12')
                                with ui.tab_panel(at_bear_az):
                                    with ui.row().classes('w-full items-center gap-4'):
                                        b_dir = ui.select(['NE', 'SE', 'SW', 'NW'], value='NE', label='Quadrant').classes('w-24')
                                        b_deg = ui.number(label='Degrees', min=0, max=90, value=45).classes('w-32')
                                        b_res = ui.label('-').classes('text-xl font-mono font-bold text-blue-700 ml-4')
                                        
                                        def reset_bear():
                                            b_dir.value = 'NE'
                                            b_deg.value = 45
                                            b_res.set_text('-')
                                        
                                        with ui.row().classes('w-full gap-2 mt-4'):
                                            ui.button('Convert', icon='transform', on_click=lambda: b_res.set_text(str(converters.bearing_to_azimuth(b_dir.value, b_deg.value)))).classes('flex-grow bg-slate-700 text-white h-12')
                                            ui.button('Reset', icon='refresh', on_click=reset_bear).classes('bg-gray-600 text-white h-12')
                    
                    with ui.column().bind_visibility_from(mode_bear, 'value', value='Batch').classes('w-full'):
                        def proc_bear(df, cols, **kwargs):
                            df['Azimuth'] = df.apply(lambda r: converters.bearing_to_azimuth(r[cols[0]], float(r[cols[1]])), axis=1)
                            return df
                        create_batch_section(input_cols_needed=2, process_callback=proc_bear)

        # --- TAB B: DISTANCE ---
        with ui.tab_panel(t_dist):
            UNITS = ['meters', 'chains', 'links', 'rods', 'us_feet', 'int_feet']
            with ui.grid(columns=2).classes('w-full gap-6'):
                # Unit Converter Section
                with ui.column().classes('w-full'):
                    ui.label('Unit Converter').classes('text-lg font-semibold mb-2')
                    mode_unit = ui.toggle(['Single', 'Batch'], value='Single').classes('w-full border-2 border-slate-200 rounded-lg p-1 bg-white mb-4')
                    
                    with ui.column().bind_visibility_from(mode_unit, 'value', value='Single').classes('w-full'):
                        with ui.card().classes('w-full p-6 bg-white shadow-md rounded-xl'):
                            with ui.row().classes('w-full gap-4'):
                                d_val = ui.number(label='Value', value=1.0).classes('flex-grow')
                                d_from = ui.select(UNITS, value='meters', label='From').classes('flex-grow')
                                d_to = ui.select(UNITS, value='int_feet', label='To').classes('flex-grow')
                            d_res = result_box("Converted Length")
                            
                            def reset_dist():
                                d_val.value = 1.0
                                d_res.set_text("Converted Length")
                            
                            with ui.row().classes('w-full gap-2 mt-4'):
                                ui.button('Convert', icon='calculate', on_click=lambda: d_res.set_text(f"{converters.convert_length(d_val.value, d_from.value, d_to.value):.4f}")).classes('flex-grow bg-blue-600 text-white h-12')
                                ui.button('Reset', icon='refresh', on_click=reset_dist).classes('bg-gray-600 text-white h-12')
                    
                    with ui.column().bind_visibility_from(mode_unit, 'value', value='Batch').classes('w-full'):
                        with ui.row().classes('w-full mb-4 bg-blue-50 p-4 rounded-lg'):
                            u_from = ui.select(UNITS, value='meters', label='From Unit').classes('w-1/2')
                            u_to = ui.select(UNITS, value='int_feet', label='To Unit').classes('w-1/2')
                        def proc_dist(df, cols, from_u, to_u):
                            df[f'Conv_{to_u}'] = df[cols[0]].apply(lambda x: converters.convert_length(float(x), from_u, to_u))
                            return df
                        create_batch_section(input_cols_needed=1, process_callback=proc_dist, from_u=u_from, to_u=u_to)
                
                # Map Scale Calculator Section
                with ui.column().classes('w-full'):
                    ui.label('Map Scale Calculator').classes('text-lg font-semibold mb-2')
                    mode_scale = ui.toggle(['Single', 'Batch'], value='Single').classes('w-full border-2 border-slate-200 rounded-lg p-1 bg-white mb-4')
                    
                    with ui.column().bind_visibility_from(mode_scale, 'value', value='Single').classes('w-full'):
                        with ui.card().classes('w-full p-6 bg-white shadow-md rounded-xl'):
                            with ui.row().classes('w-full gap-4'):
                                map_dist = ui.number(label='Map Distance (cm)', value=5.0).classes('w-1/2')
                                scale_fac = ui.number(label='Scale Factor (1:X)', value=2000).classes('w-1/2')
                            scale_res = result_box("Ground Distance (Meters)")
                            
                            def reset_scale():
                                map_dist.value = 5.0
                                scale_fac.value = 2000
                                scale_res.set_text("Ground Distance (Meters)")
                            
                            with ui.row().classes('w-full gap-2 mt-4'):
                                ui.button('Calculate', icon='calculate', on_click=lambda: scale_res.set_text(f"{converters.map_to_ground(map_dist.value, scale_fac.value):.2f} m")).classes('flex-grow bg-slate-700 text-white h-12')
                                ui.button('Reset', icon='refresh', on_click=reset_scale).classes('bg-gray-600 text-white h-12')
                    
                    with ui.column().bind_visibility_from(mode_scale, 'value', value='Batch').classes('w-full'):
                        with ui.row().classes('w-full mb-4 bg-blue-50 p-4 rounded-lg'):
                            s_fac = ui.number(label='Scale Factor (1:X)', value=2000).classes('w-full')
                        def proc_scale(df, cols, sf):
                            df['Ground_Dist_m'] = df[cols[0]].apply(lambda x: converters.map_to_ground(float(x), sf))
                            return df
                        create_batch_section(input_cols_needed=1, process_callback=proc_scale, sf=s_fac)

        # --- TAB C: COORDINATES ---
        with ui.tab_panel(t_coord):
            with ui.card().classes('w-full p-4 bg-white shadow-sm rounded-xl mb-4'):
                with ui.row().classes('w-full gap-4'):
                    src_sel = ui.select(EPSG_KEYS, label='Source CRS', value=DEFAULT_SRC, with_input=True).classes('w-1/2')
                    tgt_sel = ui.select(EPSG_KEYS, label='Target CRS', value=DEFAULT_TGT, with_input=True).classes('w-1/2')

            mode = ui.toggle(['Single', 'Batch'], value='Single').classes('w-full border-2 border-slate-200 rounded-lg p-1 bg-white mb-4')

            with ui.column().bind_visibility_from(mode, 'value', value='Single').classes('w-full'):
                with ui.row().classes('w-full gap-6'):
                    with ui.column().classes('w-full md:w-1/3'):
                        lon_in = ui.number(label='East / X', format='%.6f', value=0.0).classes('w-full')
                        lat_in = ui.number(label='North / Y', format='%.6f', value=0.0).classes('w-full')
                        c_res = ui.label('Waiting...').classes('text-xl font-bold text-blue-600 mt-6 border p-4 rounded bg-blue-50 w-full text-center')
                        
                        def run_single_coord():
                            if lon_in.value is None or lat_in.value is None:
                                ui.notify("Please enter valid coordinates", type='warning')
                                return
                            try:
                                s, t = EPSG_DICT[src_sel.value], EPSG_DICT[tgt_sel.value]
                                x, y = converters.transform_coords(lon_in.value, lat_in.value, s, t)
                                c_res.set_text(f"X: {x:.4f}\nY: {y:.4f}")
                                mx, my = converters.get_wgs84_coords(lon_in.value, lat_in.value, s)
                                map_div.content = update_map_html(mx, my)
                            except Exception as e: 
                                ui.notify(str(e), type='negative')
                        
                        def reset_coord():
                            lon_in.value = 0.0
                            lat_in.value = 0.0
                            c_res.set_text('Waiting...')
                            map_div.content = update_map_html(0, 0)
                        
                        with ui.row().classes('w-full gap-2 mt-4'):
                            ui.button('Convert', icon='transform', on_click=run_single_coord).classes('flex-grow bg-blue-600 text-white h-12')
                            ui.button('Reset', icon='refresh', on_click=reset_coord).classes('bg-gray-600 text-white h-12')

                    with ui.column().classes('w-full md:w-2/3'):
                        map_div = ui.html(update_map_html(0, 0), sanitize=False).classes('w-full h-80 border-2 border-slate-200 rounded shadow-inner')

            with ui.column().bind_visibility_from(mode, 'value', value='Batch').classes('w-full'):
                def proc_coord(df, cols, src, tgt):
                    s_code = EPSG_DICT[src]
                    t_code = EPSG_DICT[tgt]
                    col_x, col_y = cols[0], cols[1]
                    res = df.apply(lambda r: converters.transform_coords(float(r[col_x]), float(r[col_y]), s_code, t_code), axis=1)
                    df['Out_X'] = [r[0] for r in res]
                    df['Out_Y'] = [r[1] for r in res]
                    return df
                create_batch_section(input_cols_needed=2, process_callback=proc_coord, src=src_sel, tgt=tgt_sel)

        # --- TAB D: AREA ---
        with ui.tab_panel(t_area):
            mode = ui.toggle(['Single', 'Batch'], value='Single').classes('w-full border-2 border-slate-200 rounded-lg p-1 bg-white mb-4')
            AREAS = ['sq_meters', 'hectares', 'acres', 'sq_feet']

            with ui.column().bind_visibility_from(mode, 'value', value='Single').classes('w-full'):
                with ui.card().classes('w-full p-6 bg-white shadow-md rounded-xl mt-6'):
                    section_header('Area Converter')
                    with ui.row().classes('w-full gap-4'):
                        aval = ui.number(label='Value', value=1.0).classes('w-1/3')
                        a_from = ui.select(AREAS, value='hectares', label='From').classes('w-1/3')
                        a_to = ui.select(AREAS, value='acres', label='To').classes('w-1/3')
                    ares = result_box("Converted Area")
                    
                    def reset_area():
                        aval.value = 1.0
                        ares.set_text("Converted Area")
                    
                    with ui.row().classes('w-full gap-2 mt-4'):
                        ui.button('Convert', icon='calculate', on_click=lambda: ares.set_text(f"{converters.convert_area(aval.value, a_from.value, a_to.value):.4f}")).classes('flex-grow bg-blue-600 text-white h-12')
                        ui.button('Reset', icon='refresh', on_click=reset_area).classes('bg-gray-600 text-white h-12')

            with ui.column().bind_visibility_from(mode, 'value', value='Batch').classes('w-full'):
                with ui.row().classes('w-full mb-4 bg-blue-50 p-4 rounded-lg'):
                    af = ui.select(AREAS, value='hectares', label='From').classes('w-1/2')
                    at = ui.select(AREAS, value='acres', label='To').classes('w-1/2')
                def proc_area(df, cols, f, t):
                    df[f'Conv_{t}'] = df[cols[0]].apply(lambda x: converters.convert_area(float(x), f, t))
                    return df
                create_batch_section(input_cols_needed=1, process_callback=proc_area, f=af, t=at)

with ui.footer().classes('bg-slate-100 text-center py-4 text-sm text-slate-600'):
    ui.label(f'Surveyor Suite v2.1 | {__import__("datetime").date.today()}')

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title='Surveyor Suite', host='0.0.0.0', port=7860)