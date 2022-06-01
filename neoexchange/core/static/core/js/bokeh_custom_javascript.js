


function next_time_phased(period_box, phase_shift, special_vars) {
    const P = period_box.value;
    const B = phase_shift.value;
    var x = special_vars.x;
    var base_date = special_vars.data_y;
    var JD = new Date().getTime()/86400000 + 2440587.5;
    let hours = JD - base_date * 24;
    let current_phase = (hours / P);
    current_phase = current_phase - Math.floor(current_phase) + B;
    let phase_diff = x - current_phase;
    if (phase_diff < 0){
        phase_diff = phase_diff + 1;
        if (phase_diff < 0){
            phase_diff = phase_diff + 1;
        }
    }
    let hours_diff = phase_diff * P;
    return "" + hours_diff.toFixed(2) + "h";
}


function set_mag_offset(dataset_source, toggle){
    const dataset = dataset_source.data;
    const O = dataset['offset'];
    const V = dataset['v_mid']
    if (toggle.active){
        for (var i = 0; i < O.length; i++) {
            O[i] = V[0] - V[i];
        }
        toggle.label = 'Reset Offsets';
    } else {
        for (var i = 0; i < O.length; i++) {
            O[i] = 0;
        }
        toggle.label = 'Apply Predicted Offset';
    }
    dataset_source.change.emit();
}


function remove_shift_data(source, dataset_source, osource, plot, plot2){
    const data = source.data;
    const base = osource.data;
    const I = dataset_source.selected.indices;
    const T = dataset_source.data['title'];
    const O = dataset_source.data['offset'];
    const D = dataset_source.data['date'];
    const y = data['mag'];
    const el = data['err_low'];
    const eh = data['err_high'];
    const m = base['mag'];
    const me = base['mag_err'];
    const t = data['title'];
    const t2 = base['title'];
    const a = data['alpha'];
    const a2 = base['alpha']
    var selected = [];
    var offy = [];
    var selected_dates = [];
    for (let i = 0; i < I.length; i++) {
        selected[i] = T[I[i]];
        offy.push(I[i]);
        selected_dates.push(new Date(D[I[i]]));
    }
    for (let i = 0; i < a2.length; i++) {
        if (selected.includes(t2[i])){
            a2[i] = 1;
        } else {
            a2[i] = 0;
        }
    }
    for (let i = 0; i < a.length; i++) {
        if (selected.includes(t[i])){
            a[i] = 1;
        } else {
            a[i] = 0;
        }
        if (offy != []) {
            for (let k = 0; k < offy.length; k++) {
                if (t[i] == T[offy[k]]) {
                    y[i] = m[i] + O[offy[k]];
                    el[i] = m[i] - me[i] + O[offy[k]];
                    eh[i] = m[i] + me[i] + O[offy[k]];
                    k = offy.length
                } else {
                    y[i] = m[i];
                    el[i] = m[i] - me[i];
                    eh[i] = m[i] + me[i];
                }
            }
        } else {
            y[i] = m[i]
            el[i] = m[i] - me[i];
            eh[i] = m[i] + me[i];
        }
    }
    source.change.emit();
    osource.change.emit();
    if (O.some(item => item != 0)){
        plot.left[0].axis_label = 'Apparent Magnitude (Adjusted)';
    } else {
        plot.left[0].axis_label = 'Apparent Magnitude';
    }
    if (selected_dates.length == 0){
        plot.title.text = plot.title.text.split("(")[0]
        plot2.title.text = plot.title.text.split("(")[0]
    } else {
        var maxDate = new Date(Math.max.apply(null,selected_dates));
        var minDate = new Date(Math.min.apply(null,selected_dates));
        if (maxDate.valueOf() == minDate.valueOf()){
            plot.title.text = plot.title.text.split("(")[0] + "("+minDate.toISOString().slice(0,10).replace(/-/g,"")+")";
            plot2.title.text = plot.title.text.split("(")[0] + "("+minDate.toISOString().slice(0,10).replace(/-/g,"")+")";
        } else {
            plot.title.text = plot.title.text.split("(")[0] + "("+minDate.toISOString().slice(0,10).replace(/-/g,"")+"-"+maxDate.toISOString().slice(0,10).replace(/-/g,"")+")";
            plot2.title.text = plot.title.text.split("(")[0] + "("+minDate.toISOString().slice(0,10).replace(/-/g,"")+"-"+maxDate.toISOString().slice(0,10).replace(/-/g,"")+")";
        }

    }
}


function link_period(p_source, period_box, period_slider, p_max, p_min){
    if (p_min.value < 0){
        p_min.value = 0;
    }
    if (p_max.value <= p_min.value){
        p_max.value = p_min.value + 1;
    }
    period_slider.end = p_max.value;
    period_slider.start = p_min.value;
    if (period_slider.value < p_min.value){
        period_slider.value = p_min.value;
    }
    if (period_slider.value > p_max.value){
        period_slider.value = p_max.value;
    }
    period_slider.step = ((p_max.value - p_min.value) / 1000 );
    period_box.step = ((p_max.value - p_min.value) / 1000 );
}


function phase_data(source, period_box, period_slider, plot, osource, phase_shift, base_date, p_mark_source){
    if (period_box.value <= 0){
        period_box.value = 0;
    }
    const B = phase_shift.value;
    const data = source.data;
    const base = osource.data;
    const mark = p_mark_source.data;
    const x = data['time'];
    const d = base['time'];
    const y = data['mag'];
    const m = base['mag'];
    const el = data['err_low'];
    const eh = data['err_high'];
    const me = data['mag_err'];
    const t = data['title'];
    const a = data['alpha'];
    const c = data['color'];
    const pm = mark['period']
    const period = period_box.value;
    period_slider.value = period_box.value;
    let pos = d.length - 1;
    let n = x.length - d.length;
    x.splice(pos,n);
    y.splice(pos,n);
    el.splice(pos,n);
    eh.splice(pos,n);
    a.splice(pos,n);
    t.splice(pos,n);
    c.splice(pos,n);
    me.splice(pos,n);
    if (period > 0) {
        for (var i = 0; i < d.length; i++){
            x[i] = (d[i] / period);
            x[i] = x[i] - Math.floor(x[i]);
            x[i] = x[i] + B;
            if (x[i] > 1.0){
                x[i] = x[i] - 1.0;
            } else if (x[i] < 0.0){
                x[i] = x[i] + 1.0;
            }
            if ((x[i] > 0.0) && (x[i] < 0.5)){
                x.push(x[i] + 1.0);
            } else if ((x[i] < 1.0) && (x[i] > 0.5)){
                x.push(x[i] - 1.0);
            }
            y.push(y[i]);
            el.push(el[i]);
            eh.push(eh[i]);
            a.push(a[i]);
            t.push(t[i]);
            c.push(c[i]);
            me.push(c[i]);
        }
    } else{
        for (var i = 0; i < d.length; i++){
            if (i <= (d.length - 1)){
                x[i] = d[i];
            }
        }
    }
    let epoch = base_date + (B * period / 24);
    plot.below[0].axis_label = 'Phase (Period = ' + period + 'h / Epoch = '+ epoch + ')';
    source.change.emit();
    for (var i = 0; i < pm.length; i++){
        pm[i] = period;
    }
    p_mark_source.change.emit();
}


function remove_shift_model(source_list, model_source, lines){
    const models = source_list;
    const I = model_source.selected.indices;
    const N = model_source.data['name'];
    const O = model_source.data['offset'];
    var selected = [];
    for (let i = 0; i < I.length; i++) {
        selected[i] = N[I[i]];
    }
    for (var i = 0; i < lines.length; i++){
        var source = models[i];
        var n = source.data['name'];
        var mag = source.data['mag'];
        var omag = source.data['omag'];
        if (selected.includes(lines[i].name)) {
            lines[i].visible = true;
            var j = N.indexOf(lines[i].name);
            for (let k = 0; k < mag.length; k++) {
                mag[k] = omag[k] + O[j];
            }
        } else {
            lines[i].visible = false
        }

        source.change.emit();
    }
}


function rotation_tool(){
    // Javascript function to rotate a DataSource based on mouse movement
    import {GestureTool, GestureToolView} from "models/tools/gestures/gesture_tool"
    import {ColumnDataSource} from "models/sources/column_data_source"
    import {PanEvent} from "core/ui_events"
    import * as p from "core/properties"

    function rotate(coords:any, omega:number, phi:number) {
        //Function to perform actual rotation
        // coords = ColumnDataSource containing datasets = {<header>_x/y/z: []}
        // omega => rotation angle around y axis
        // phi => rotation angle around x axis
        const theta = 0  // rotation angle around z axis
        const ct = Math.cos(theta)
        const st = Math.sin(theta)
        const cp = Math.cos(phi)
        const sp = Math.sin(phi)
        const co = Math.cos(omega)
        const so = Math.sin(omega)
        const keys = Object.keys(coords.data) as string[]
        const unique_keys = [] as string[]
        var key
        for (key of keys) {
            // pull out coordinate header
            const first = key.split("_")
            if (first.length > 1 && unique_keys.indexOf(first[0]) == -1) {
                unique_keys.push(first[0])
                // separate individual coordinates from face data
                if (typeof coords.get_array(first[0].concat("_x"))[0] == "number") {
                    var xx_list = [coords.get_array(first[0].concat("_x")) as number[]]
                    var yy_list = [coords.get_array(first[0].concat("_y")) as number[]]
                    var zz_list = [coords.get_array(first[0].concat("_z")) as number[]]
                } else {
                    var xx_list = coords.get_array(first[0].concat("_x")) as number[][]
                    var yy_list = coords.get_array(first[0].concat("_y")) as number[][]
                    var zz_list = coords.get_array(first[0].concat("_z")) as number[][]
                }
                var level = [] as any[];
                // Perform Rotation
                for (var k = 0; k < xx_list.length; k++){
                    var xx = xx_list[k]
                    var yy = yy_list[k]
                    var zz = zz_list[k]
                    for (var i = 0; i < xx.length; i++){
                        const xx_out = (xx[i] * ct * co) + (yy[i] * (ct * so * sp - st * cp)) + (zz[i] * (ct * so * cp + st * sp))
                        const yy_out = (xx[i] * st * co) + (yy[i] * (st * so * sp + ct * cp)) + (zz[i] * (st * so * cp - ct * sp))
                        const zz_out = (yy[i] * (co * sp)) + (zz[i] * (co * cp)) - (xx[i] * so)
                        xx[i] = xx_out
                        yy[i] = yy_out
                        zz[i] = zz_out
                    }
                    level.push({index: k, value: Math.min(...zz)});
                }
                // Sort faces by min z
                level.sort(function(a, b){return a.value - b.value})
                var k2
                for (k2 of keys){
                    if (k2.includes(first[0])){
                        if (level.length > 1){
                            var to_sort = coords.data[k2]
                            to_sort = level.map(function(e:any){return to_sort[e.index];})
                            coords.data[k2] = to_sort
                        }
                    }
                }
            }
        }
    }

    export class RotToolView extends GestureToolView {
      model: RotTool

      //this is executed when the pan/drag event starts
      _pan_start(_ev: PanEvent): void {
        this.model.source.data = {x: [], y: []}
      }

      //this is executed on subsequent mouse/touch moves
      _pan(ev: PanEvent): void {
        const {frame} = this.plot_view

        const {sx, sy} = ev

        if (!frame.bbox.contains(sx, sy))
          return

        const {source, coords_list} = this.model

        const x_list = source.get_array("x") as number[]
        const y_list = source.get_array("y") as number[]

        var omega = 0
        var phi = 0
        const scale = .01

        x_list.push(sx)
        y_list.push(sy)

        //Translate x/y mouse movement from pixel position to rotation angle
        if (x_list.length > 2) {
            x_list.shift()
            y_list.shift()
            var omega = (x_list[1] - x_list[0]) * scale
            var phi = (y_list[1] - y_list[0]) * scale
            }

        var coords
        for (coords of coords_list) {
            // Perform Rotation
            rotate(coords, omega, phi)
            // Update DataSources
            coords.change.emit()
        }

        // Update mouse position
        source.change.emit()
      }

      // this is executed then the pan/drag ends
      _pan_end(_ev: PanEvent): void {}
    }

    export namespace RotTool {
      export type Attrs = p.AttrsOf<Props>

      export type Props = GestureTool.Props & {
        source: p.Property<ColumnDataSource>,
        coords_list: p.Property<ColumnDataSource>
      }
    }

    export interface RotTool extends RotTool.Attrs {}

    export class RotTool extends GestureTool {
      properties: RotTool.Props
      __view_type__: RotToolView

      constructor(attrs?: Partial<RotTool.Attrs>) {
        super(attrs)
      }

      tool_name = "Rotate Tool"
      icon = "bk-tool-icon-wheel-pan"
      event_type = "pan" as "pan"
      default_order = 12

      static init_RotTool(): void {
        this.prototype.default_view = RotToolView

        this.define<RotTool.Props>({
          source: [ p.Instance ],
          coords_list: [ p.Instance ],
        })
      }
    }
}


function analog_select(analog_select, frame_select, reflectance_sources, chosen_sources, plot, plot2, lines, raw_analog, raw_analog_list, raw_lines){
    const analog = analog_select.value;
    const options = analog_select.options;
    const frames = frame_select.value;

    for (var i = 0; i < options.length; i++){
        if (analog == options[i]){
            raw_analog.data['spec'] = raw_analog_list[i].data['spec'];
            raw_analog.data['wav'] = raw_analog_list[i].data['wav'];
            for (var k = 0; k < chosen_sources.length; k++){
                chosen_sources[k].data['spec'] = reflectance_sources[k][i].data['spec'];
                chosen_sources[k].data['wav'] = reflectance_sources[k][i].data['wav'];
                var num = k+1;
                if (frames.includes(num.toString())){
                    raw_lines[k].muted=false
                    lines[k].visible = true
                } else {
                    raw_lines[k].muted=true
                    lines[k].visible = false
                }
                chosen_sources[k].change.emit();
                lines[k].change.emit()
            }
            raw_analog.change.emit()
            plot.title.text = plot.title.text.split("    ")[0] + "    Analog: " + analog;
            plot2.title.text = plot2.title.text.split("    ")[0] + "    Analog: " + analog;
        }
    }
}


function contrast_switch(toggle, plots){
    for (var plot of plots){
        if (toggle.active){
            plot.glyph.fill_color = "gray";
            plot.glyph.line_color = "black";
            toggle.label = 'Apply Shading';
        } else {
            plot.glyph.fill_color = {'field':'faces_colors'};
            plot.glyph.line_color = {'field':'faces_colors'};
            toggle.label = 'Remove Shading';
        }
    }
}


function shape_select(selector, plots, labels, poles){
    const label_text = labels.data['text']

    for (var i = 0; i < plots.length; i++){
        if (Number(selector.value) == i+1){
            plots[i].visible = true;
            const long_deg = poles[i]["p_long"][0] / Math.PI * 180
            const lat_deg = poles[i]["p_lat"][0] / Math.PI * 180 + 90
            label_text[1] = '(' + long_deg.toFixed(1) + ', ' + lat_deg.toFixed(1) + ')'
            label_text[5] = poles[i]["period_fit"][0] + 'h'
            labels.change.emit()
        } else {
            plots[i].visible = false;
        }
    }
}


function shading_slider(source, orbit_slider, rot_slider, long_asc, inc, sn, prev_rot, orient, label){
    // CustomJS to adjust shading and rotation of shape model.
    const model_num = Number(sn.value-1)
    const dataset = source[model_num].data;
    const pr = prev_rot.data['prev_rot'];
    const orient_data = orient[model_num].data
    const pole_vector = [orient_data['v_x'][0], orient_data['v_y'][0], orient_data['v_z'][0]];
    const C = dataset['faces_colors'];
    const N = dataset['faces_normal'];
    const pole_long = orient_data['p_long'][0];
    const pole_lat = orient_data['p_lat'][0];

    // set orbital angles
    const orb_phase = orbit_slider.value;
    const orb_angle = orb_phase * 2 * Math.PI + long_asc - pole_long;
    const elev = Math.sin(orb_phase * 2 * Math.PI) * inc;
    const sol_omega = Math.cos(orb_angle) * elev - pole_lat;  // rotation angle around y axis
    const sol_phi = Math.sin(orb_angle) * elev; // rotation angle around x axis
    const sol_theta = orb_angle;  // rotation angle around z axis

    // Set rotational angles
    const rot_phase = rot_slider.value;
    const rot_angle = rot_phase * 2 * Math.PI;
    const ast_omega = 0; // rotation angle around y axis
    const ast_phi = 0; // rotation angle around x axis
    const ast_theta = rot_angle; // rotation angle around z axis

    function rotate(coords, omega, phi, theta, colors){
        // Function to perform rotation of normals
        // coords => array of normal vectors
        // omega => rotation angle around y axis
        // phi => rotation angle around x axis
        // theta => rotation angle around z axis
        const ct = Math.cos(theta)
        const st = Math.sin(theta)
        const cp = Math.cos(phi)
        const sp = Math.sin(phi)
        const co = Math.cos(omega)
        const so = Math.sin(omega)
        var N_out = []
        // Perform Rotation
        for (var k = 0; k < coords.length; k++){
            var xx = coords[k][0]
            var yy = coords[k][1]
            var zz = coords[k][2]
            const xx_out = (xx * ct * co) + (yy * (ct * so * sp - st * cp)) + (zz * (ct * so * cp + st * sp))
            const yy_out = (xx * st * co) + (yy * (st * so * sp + ct * cp)) + (zz * (st * so * cp - ct * sp))
            const zz_out = (yy * (co * sp)) + (zz * (co * cp)) - (xx * so)
            var brightness = xx_out * 100;
            colors[k] ="hsl(0, 0%, " + brightness + "%)";
            N_out.push([xx_out, yy_out, zz_out]);
        }
        return N_out;
    }

    function pole_rotate(coords, theta, pole){
        // rotate faces around pole
        // coords => ColumnDataSource containing datasets = {<header>_x/y/z: []}
        // theta => rotation around pole
        // pole => unit vector representing the pole direction
        const ct = Math.cos(theta)
        const cti = 1 - Math.cos(theta)
        const st = Math.sin(theta)
        const px = pole[0]
        const py = pole[1]
        const pz = pole[2]
        const keys = Object.keys(coords.data)
        const unique_keys = []
        var key
        for (key of keys) {
            // pull out coordinate header
            const first = key.split("_")
            if (first.length > 1 && unique_keys.indexOf(first[0]) == -1) {
                unique_keys.push(first[0])
                var xx_list = coords.get_array(first[0].concat("_x"))
                var yy_list = coords.get_array(first[0].concat("_y"))
                var zz_list = coords.get_array(first[0].concat("_z"))
                var level = [];
                // Perform Rotation
                for (var k = 0; k < xx_list.length; k++){
                    var xx = xx_list[k]
                    var yy = yy_list[k]
                    var zz = zz_list[k]
                    // Pull out linear algebra text book
                    // Implement Rodrigues' rotation formula for rotation around "arbitrary" axis.
                    for (var i = 0; i < xx.length; i++){
                        const xx_out = (xx[i] * (px * px * cti + ct)) + (yy[i] * (px * py * cti - pz * st)) + (zz[i] * (px * pz * cti + py * st))
                        const yy_out = (xx[i] * (px * py * cti + pz * st)) + (yy[i] * (py * py * cti + ct)) + (zz[i] * (py * pz * cti - px * st))
                        const zz_out = (xx[i] * (px * pz * cti - py * st)) + (yy[i] * (py * pz * cti + px * st)) + (zz[i] * (pz * pz * cti + ct))
                        xx[i] = xx_out
                        yy[i] = yy_out
                        zz[i] = zz_out
                    }
                    level.push({index: k, value: Math.min(...zz)});
                }
                // Sort faces by min z
                level.sort(function(a, b){return a.value - b.value})
                var k2
                for (k2 of keys){
                    if (k2.includes(first[0])){
                        if (level.length > 1){
                            var to_sort = coords.data[k2]
                            to_sort = level.map(function(e){return to_sort[e.index];})
                            coords.data[k2] = to_sort
                        }
                    }
                }
            }
        }
    }

    // rotate asteroid shading around pole
    const rotated_N = rotate(N, ast_omega, ast_phi, ast_theta, C)
    // rotate sun direction as asteroid orbits
    rotate(rotated_N, sol_omega, sol_phi, sol_theta, C)
    // rotate asteroid faces around pole to match view
    pole_rotate(source[model_num], ast_theta - pr[model_num], pole_vector)

    // store rotation state
    pr[model_num] = ast_theta;
    prev_rot.change.emit()
    // update shading/orientation
    source[model_num].change.emit()
    // update heliocentric position label
    const label_text = label.data['text'];
    var long_deg = (orb_phase * 2 * Math.PI + long_asc) * 180 / Math.PI
    const lat_deg = elev * 180 / Math.PI
    if (long_deg > 360){
        long_deg -= 360
    } else if (long_deg < 0){
        long_deg += 360
    }
    label_text[3] = '(' + long_deg.toFixed(1) + ', ' + lat_deg.toFixed(1) + ')'
    label.change.emit()
}

function u_plot_xaxis_scale(plot){
    // change x_axis units on zoom
    // plot => unphased plot. Requires 3 axes below plot.
    const max = plot.x_range['end']
    const min = plot.x_range['start']
    const range = max-min
    if (range < .5){
        plot.below[0]['visible'] = false
        plot.below[1]['visible'] = false
        plot.below[2]['visible'] = true
    } else if (range < 200){
        plot.below[0]['visible'] = true
        plot.below[1]['visible'] = false
        plot.below[2]['visible'] = false
    } else{
        plot.below[0]['visible'] = false
        plot.below[1]['visible'] = true
        plot.below[2]['visible'] = false
    }
}