'''
NEO exchange: NEO observing portal for Las Cumbres Observatory Global Telescope Network
Copyright (C) 2014-2015 LCOGT

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''

from datetime import datetime
from django.test import TestCase
from django.forms.models import model_to_dict
from django.contrib.auth.models import User
from django.test import TestCase
from django.test.client import RequestFactory, Client

from unittest import skipIf
import os
from mock import patch
from neox.tests.mocks import mock_rbauth_login
from core.models import Proposal, ProposalPermission
from neox.auth_backend import checkUserObject, rbauth_login, parse_proposals, \
    update_proposal_permissions, LCOAuthBackend
from core.views import user_proposals


class Test_Auth(TestCase):

    def setUp(self):
        proposal_params1 = {
                'code': 'LCOTEST1',
                'title' : 'Test Proposal #1',
                'pi' : 'test.user',
                'tag' : 'LCOGT',
                'active': True
                        }
        proposal_params2 = {
                'code': 'LCOTEST2',
                'title' : 'Test Proposal #2',
                'pi' : 'test.user',
                'tag' : 'LCOGT',
                'active': True
                        }
        proposal_params3 = {
                'code': 'LCOTEST3',
                'title' : 'Test Proposal - inactive',
                'pi' : 'test.user',
                'tag' : 'LCOGT',
                'active': False
                        }
        p1 = Proposal(**proposal_params1)
        p1.save()

        p2 = Proposal(**proposal_params2)
        p2.save()

        p3 = Proposal(**proposal_params3)
        p3.save()

        self.proposal1 = p1
        self.proposal2 = p2
        self.proposal_inactive = p3

    @patch('neox.auth_backend.rbauth_login', mock_rbauth_login)
    def test_user_login(self):
        self.assertTrue(self.client.login(username='bart', password='simpson'))

    @patch('neox.auth_backend.rbauth_login', mock_rbauth_login)
    def test_login_proposals(self):
        # When Bart logs in, he gets 1 proposal, LCOTEST1
        self.client.login(username='bsimpson', password='simpson')
        bart = User.objects.get(username='bsimpson')
        saved_proposals = user_proposals(bart)
        # Check the same proposals go in as come out
        self.assertEqual(set([self.proposal1]), set(saved_proposals))

    @patch('neox.auth_backend.rbauth_login', mock_rbauth_login)
    def test_adding_user_to_proposal(self):
        # Add Bart to a different proposal to the one he already had
        self.client.login(username='bsimpson', password='simpson')
        bart = User.objects.get(username='bsimpson')
        # Proposals have to be Dicts not objects
        new_proposal = [self.proposal2.__dict__]
        update_proposal_permissions(bart, new_proposal)
        saved_proposals = user_proposals(bart)
        # Check the same proposals go in as come out
        self.assertEqual(set([self.proposal2]), set(saved_proposals))

    @patch('neox.auth_backend.rbauth_login', mock_rbauth_login)
    def test_adding_user_two_proposal(self):
        # Add Bart to 2 proposals, he's already a member of 1
        self.client.login(username='bsimpson', password='simpson')
        bart = User.objects.get(username='bsimpson')
        # Proposals have to be Dicts not objects
        new_proposals = [self.proposal1.__dict__, self.proposal2.__dict__]
        update_proposal_permissions(bart, new_proposals)
        saved_proposals = user_proposals(bart)
        # Check the same proposals go in as come out
        self.assertEqual(set([self.proposal1, self.proposal2]), set(saved_proposals))

    @patch('neox.auth_backend.rbauth_login', mock_rbauth_login)
    def test_adding_user_two_proposal_inactive(self):
        # Add Bart to 2 proposals, he's already a member of 1, the other is inactive
        self.client.login(username='bsimpson', password='simpson')
        bart = User.objects.get(username='bsimpson')
        # Proposals have to be Dicts not objects
        new_proposals = [self.proposal1.__dict__, self.proposal_inactive.__dict__]
        update_proposal_permissions(bart, new_proposals)
        saved_proposals = user_proposals(bart)
        # The inactive proposal should not have been added
        self.assertEqual(set([self.proposal1]), set(saved_proposals))
