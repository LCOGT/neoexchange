"""
This file was generated with the customdashboard management command and
contains the class for the main dashboard.

To activate your index dashboard add the following to your settings.py::
    GRAPPELLI_INDEX_DASHBOARD = 'neoexchange.dashboard.CustomIndexDashboard'
"""

from django.utils.translation import gettext_lazy as _

from grappelli.dashboard import modules, Dashboard


class CustomIndexDashboard(Dashboard):
    """
    Custom index dashboard for NEO Exchange
    """
    
    def init_with_context(self, context):
        site_name = "NEO Exchange"  # get_admin_site_name(context)
        
        # append a group for "Administration" & "Applications"
        self.children.append(
            modules.Group(_('Group: Administration & Applications'),
                          column=1,
                          collapsible=True,
                          children=[modules.AppList(_('Administration'),
                                                    column=1,
                                                    collapsible=False,
                                                    models=('django.contrib.*',),
                                                    ),
                                    modules.AppList(_('Applications'),
                                                    column=1,
                                                    css_classes=('collapse closed',),
                                                    exclude=('django.contrib.*',),
                                                    )
                                    ]
                          )
        )
        
        # append an app list module for "Applications"
        self.children.append(modules.AppList(_('AppList: Applications'),
                                             collapsible=True,
                                             column=1,
                                             css_classes=('collapse closed',),
                                             exclude=('django.contrib.*',),
                                             )
                             )
        
        # append an app list module for "Administration"
        self.children.append(modules.ModelList(_('ModelList: Administration'),
                                               column=1,
                                               collapsible=False,
                                               models=('django.contrib.*',),
                                               )
                             )
        
        # append another link list module for "support".
        self.children.append(modules.LinkList(_('Related'),
                                              column=2,
                                              children=[
                                                  {'title': _('LCO main site'),
                                                   'url': 'http://lco.global/',
                                                   'external': True,
                                                   },
                                                  {'title': _('Observing Portal'),
                                                   'url': 'http://lco.global/observe/',
                                                   'external': True,
                                                   },
                                              ]
                                              )
                             )
        
        # append a recent actions module
        self.children.append(modules.RecentActions(_('Recent Actions'),
                                                   limit=5,
                                                   collapsible=False,
                                                   column=2,
                                                   )
                             )
