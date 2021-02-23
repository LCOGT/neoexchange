


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
    let hours_diff = phase_diff * P
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


function link_period(period_box, period_slider, p_max, p_min){
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


function phase_data(source, period_box, period_slider, plot, osource, phase_shift, base_date){
    if (period_box.value <= 0){
        period_box.value = 0;
    }
    const B = phase_shift.value;
    const data = source.data;
    const base = osource.data;
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
}
