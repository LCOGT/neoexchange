# NEOexchange Processing Pipeline

## Pipeline Stages

Pipeline stage  Inputs                          Outputs                 Codes used
-----------------------------------------------------------------------------------
proc-extract    e91.fits                        e91.rms.fits            sextractor
                Frame.BANZAI_RED_FRAMETYPE      e91_ldac.fits

proc-astromfit  e91_ldac.fits                   e92.fits                scamp
                                                (Image with new WCS)
                                                e92.rms.fits (Not needed?)
                                                e92_ldac.fits
                                                (Catalog from image with new WCS)
                                                scamp.xml
                                                e91_ldac.head
proc-zeropoint  e92_ldac.fits                   Updated e92.fits        calviacat                                    
                                                Frame.NEOX_RED_FRAMETYPE
                                                Frame.BANZAI_LDAC_CATALOG
