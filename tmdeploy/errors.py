# TmDeploy - Automated deployment of TissueMAPS in the cloud.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
class SetupDescriptionError(Exception):
    '''Exception class for erronous setup description.'''


class SetupEnvironmentError(Exception):
    '''Exception class for missing environment variables required for setup.'''


class CloudError(Exception):
    '''Error class for interactions with cloud clients.'''


class NoInstanceFoundError(CloudError):
    '''Error class for situations where no matching instance is found.'''


class MultipleInstancesFoundError(CloudError):
    '''Error class for situations where multiple matching instances are found.'''

