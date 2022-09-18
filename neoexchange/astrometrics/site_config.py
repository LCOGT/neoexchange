

# Field of view is in arcmin, pixel scale is in arcsec
tel_field = {   'onem_fov'              : 15.5,
                'onem_pixscale'         : 0.464,
                'onem_sinistro_fov'     : 26.4,
                'onem_sinistro_pixscale': 0.389,
                'onem_2x2_sinistro_fov' : 13.2,
                'onem_2x2_sin_pixscale' : 0.778,
                'onem_fli_fov'          : 5.82,
                'onem_fli_pixscale'     : 0.341,
                'point4m_pixscale'      : 0.571,        # bin 2, from average kb29 values = 1.139/ 1x1 nominal = 0.58 / 1x1 from average of kb27 = 0.571
                'point4m_fov'           : 29.1,
                'twom_pixscale'         : 0.304,
                'twom_fov'              : 10.0,
                'twom_muscat_pixscale'  : 0.27,
                'twom_muscat_fov'       : 9.1,
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
                 'twom_setup_overhead'      : 180.0,                 # front padding
                 'point4m_setup_overhead'   : 90.0,                  # front padding
               }

# Per-Instrument overheads (s)
inst_overhead = {   'onemsbig_exp_overhead'         : 15.5,
                    'point4m_exp_overhead'          : 13.0 + 1.0,       # readout + fixed overhead/exposure
                    'sinistro_exp_overhead'         : 27.0 + 1.0,       # readout + fixed overhead/exposure
                    'sinistro_2x2_exp_overhead'     : 8.0 + 1.0,        # readout + fixed overhead/exposure
                    'twom_exp_overhead'             : 10.5 + 8.5,       # readout + fixed overhead/exposure
                    'muscat_exp_overhead'           : 10,               # TBD
                    'floyds_exp_overhead'           : 25.0 + 0.5,       # readout + fixed overhead/exposure
                    'floyds_config_change_overhead' : 60.0,
                    'floyds_acq_proc_overhead'      : 60.0,
                    'floyds_acq_exp_time'           : 30.0,
                    'floyds_calib_exp_time'         : 60.0
                }

# Telescope sites
valid_site_codes = { 'ELP-DOMA-1M0A' : 'V37',
                     'ELP-DOMB-1M0A' : 'V39',
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
                     'TFN-DOMA-1M0A' : 'Z31',
                     'TFN-DOMB-1M0A' : 'Z24',
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
                     'SQA-DOMA-0M8A' : 'G51',
                     'XXX-XXXX-1M0X' : '1M0',
                     'XXX-XXXX-0M4X' : '0M4',
                     'XXX-XXXX-2M0X' : '2M0'}

# Reverse site code dictionary
valid_telescope_codes = {v: k for k, v in valid_site_codes.items()}

# Telescope serial codes
valid_telescope_serials = {  '1m008' : 'V37',
                             '1m006' : 'V39',
                             '1m005' : 'W85',
                             '1m009' : 'W86',
                             '1m004' : 'W87',
                             '1m010' : 'K91',
                             '1m013' : 'K92',
                             '1m012' : 'K93',
                             '1m011' : 'Q63',
                             '1m003' : 'Q64',
                             '2m001' : 'F65',
                             '2m002' : 'E10',
                             '1m014' : 'Z31',
                             '1m001' : 'Z24',
                             '0m414' : 'Z21',
                             '0m410' : 'Z17',
                             '0m403' : 'Q58',
                             '0m405' : 'Q59',
                             '0m406' : 'T04',
                             '0m404' : 'T03',
                             '0m409' : 'W89',
                             '0m412' : 'W79',
                             '0m411' : 'V38',
                             '0m407' : 'L09', # LCOGT   cpt-aqwa-0m4a
                             '0m420' : 'XXX'  # ASAS-SN cpt-aqwa-0m4b
                            }

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

science_cams = [    "1m0-SciCam-Sinistro",
                    "2m0-FLOYDS-SciCam",
                    "2m0-SciCam-Spectral",
                    "2m0-SciCam-MuSCAT",
                    "0m4-SciCam-SBIG"
                ]
