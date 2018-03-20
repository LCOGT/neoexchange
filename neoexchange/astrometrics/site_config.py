

#Field of view is in arcmin, pixel scale is in arcsec
tel_field = {   'onem_fov'              : 15.5,
                'onem_pixscale'         : 0.464,
                'onem_sinistro_fov'     : 26.4,
                'onem_sinistro_pixscale' : 0.389,
                'point4m_pixscale'      : 1.139,        # bin 2, from average kb29 values
                'point4m_fov'           : 29.1,
                'twom_pixscale'         : 0.304,
                'twom_fov'              : 10.0
            }

#altitude limits
tel_alt = { 'normal_alt_limit'  : 30.0,
            'twom_alt_limit'    : 20.0,
            'point4m_alt_limit' : 15.0
          }

#molecule overheads (s)
molecule_overhead = {   'filter_change'     : 2.0,                         #time required to change filter
                        'per_molecule_time' : 5.0 + 11.0                   #per molecule gap + Molecule start up time
                    }

# Per-Telescope overheads (s)
tel_overhead = { 'onem_setup_overhead'      : 90.0,                  # front padding 
                 'twom_setup_overhead'      : 240.0,                 # front padding
                 'point4m_setup_overhead'   : 90.0,                  # front padding
               }

# Per-Instrument overheads (s)
inst_overhead = {   'onemsbig_exp_overhead'         : 15.5,
                    'point4m_exp_overhead'          : 13.0 + 1.0,       # readout + fixed overhead/exposure
                    'sinistro_exp_overhead'         : 37.0 + 1.0,      # readout + fixed overhead/exposure
                    'twom_exp_overhead'             : 10.5 + 8.5,          # readout + fixed overhead/exposure
                    'floyds_exp_overhead'           : 25.0 + 0.5,        # readout + fixed overhead/exposure
                    'floyds_config_change_overhead' : 30.0,
                    'floyds_acq_proc_overhead'      : 60.0,
                    'floyds_acq_exp_time'           : 30.0,
                    'floyds_calib_time'             : 60.0
                }
