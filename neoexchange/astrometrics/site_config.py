

# Field of view is in arcmin, pixel scale is in arcsec
tel_field = {   'onem_fov'              : 15.5,
                'onem_pixscale'         : 0.464,
                'onem_sinistro_fov'     : 26.4,
                'onem_sinistro_pixscale' : 0.389,
                'point4m_pixscale'      : 0.571,        # bin 2, from average kb29 values = 1.139/ 1x1 nominal = 0.58 / 1x1 from average of kb27 = 0.571
                'point4m_fov'           : 29.1,
                'twom_pixscale'         : 0.304,
                'twom_fov'              : 10.0,
                'twom_floyds_pixscale'  : 0.337,
                'twom_floyds_fov'       : 2.0
            }

# altitude limits
tel_alt = { 'normal_alt_limit'  : 30.0,
            'twom_alt_limit'    : 20.0,
            'point4m_alt_limit' : 15.0
          }

# molecule overheads (s)
molecule_overhead = {   'filter_change'     : 2.0,                         # time required to change filter
                        'per_molecule_time' : 5.0 + 11.0                   # per molecule gap + Molecule start up time
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
                    'floyds_calib_exp_time'         : 60.0
                }

# Telescope sites
valid_site_codes = { 'ELP-DOMA-1M0A' : 'V37',
                     'LSC-DOMA-1M0A' : 'W85',
                     'LSC-DOMB-1M0A' : 'W86',
                     'LSC-DOMC-1M0A' : 'W87',
                     'CPT-DOMA-1M0A' : 'K91',
                     'CPT-DOMB-1M0A' : 'K92',
                     'CPT-DOMC-1M0A' : 'K93',
                     'COJ-DOMA-1M0A' : 'Q63',
                     'COJ-DOMB-1M0A' : 'Q64',
                     'OGG-CLMA-2M0A' : 'F65',
                     'COJ-CLMA-2M0A' : 'E10',
                     'TFN-AQWA-0M4A' : 'Z21',
                     'TFN-AQWA-0M4B' : 'Z17',
                     'COJ-CLMA-0M4A' : 'Q58',
                     'COJ-CLMA-0M4B' : 'Q59',
                     'OGG-CLMA-0M4B' : 'T04',
                     'OGG-CLMA-0M4C' : 'T03',
                     'LSC-AQWA-0M4A' : 'W89',
                     'LSC-AQWB-0M4A' : 'W79',
                     'ELP-AQWA-0M4A' : 'V38',
                     'CPT-AQWA-0M4A' : 'L09',
                     'SQA-DOMA-0M8A' : 'G51'}

# Reverse site code dictionary
valid_telescope_codes = {v: k for k, v in valid_site_codes.items()}

# Establish Filter Lists
phot_filters = [    "air",
                    "clear",
                    "ND",
                    "Astrodon-UV",
                    "U",
                    "B",
                    "V",
                    "R",
                    "I",
                    "B*ND",
                    "V*ND",
                    "R*ND",
                    "I*ND",
                    "up",
                    "gp",
                    "rp",
                    "ip",
                    "Skymapper-VS",
                    "solar",
                    "zs",
                    "Y",
                    "w"
                    ]

spec_filters = [    "slit_1.2as",
                    "slit_1.6as",
                    "slit_2.0as",
                    "slit_6.0as"
                ]
