from django.core.management.base import BaseCommand, CommandError
from core.models import Body
from core.models import PhysicalParameters
from astropy.table import Table
from photometrics.gf_movie import print_progress_bar
from datetime import datetime

class Command(BaseCommand):
    #table = Table.read('NEOs.csv')

    def handle(self, *args, **options):
        self.stdout.write("=== Populating Bodies from JPL %s ===")
        time_in = datetime.now()
        table = Table.read('NEOs.csv')
        for i, rock in enumerate(table):
            body_params = { 'name' : rock['full_name'],
                            #'(semimajor axis?)' : rock['a'],
                            'eccentricity' : rock['e'],
                            'orbinc' : rock['i'],
                            #'lonascnode' : rock['om'],
                            'argofperih' : rock['w'],
                            'perihdist' : rock['q'],
                            'meandist' : rock['ad'],
                            #'period (in years)' : rock['per_y'],
                            'arc_length' : rock['data_arc'],
                            'abs_mag' : rock['H'],
                            }
            new_body, created = Body.objects.get_or_create(**body_params) 

            print_progress_bar(i+1, len(table), time_in=time_in)
                   
            phys_par = {'parameter_type' : 'D', 'value' : rock['diameter'], 'body' : new_body
                        }           
            
            phys_par, created = PhysicalParameters.objects.get_or_create(**phys_par)
            
            phys_par = {'parameter_type' : 'P', 'value' : rock['rot_per'], 'body' : new_body
                        }           
            
            phys_par, created = PhysicalParameters.objects.get_or_create(**phys_par)
       








   
