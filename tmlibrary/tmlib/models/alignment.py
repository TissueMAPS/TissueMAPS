# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016-2018 University of Zurich.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import logging
from sqlalchemy import Column, Integer, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import relationship, backref

from tmlib.models.base import ExperimentModel


logger = logging.getLogger(__name__)


class SiteShift(ExperimentModel):

    '''Translation of a given :class:`Site <tmlib.models.site.Site>` acquired
    at a given :class:`Cycle <tmlib.models.cycle.Cycle>`
    relative to the corresponding :class:`Site <tmlib.models.site.Site>` of
    the reference :class:`Cycle <tmlib.models.cycle.Cycle>`.'''

    __tablename__ = 'site_shifts'

    __table_args__ = (PrimaryKeyConstraint('site_id', 'cycle_id'), )

    #: int: horizontal translation in pixels relative to the corresponding
    #: site of the reference cycle
    #: (positive value -> right, negative value -> left)
    y = Column(Integer)

    #: int: vertical translation in pixels relative to the corresponding
    #: site of the reference cycle
    #: (positive value -> down, negative value -> up)
    x = Column(Integer)

    #: int: ID of the parent site
    site_id = Column(
        Integer,
        ForeignKey('sites.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    #: int: ID of the parent cycle
    cycle_id = Column(
        Integer,
        ForeignKey('cycles.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    #: tmlib.models.site.Site: parent site for which the shift was calculated
    site = relationship(
        'Site',
        backref=backref('shifts', cascade='all, delete-orphan')
    )

    #: tmlib.models.cycle.Cycle: parent cycle for which the shift was calculated
    cycle = relationship(
        'Cycle',
        backref=backref('site_shifts', cascade='all, delete-orphan')
    )

    def __init__(self, x, y, site_id, cycle_id):
        '''
        Parameters
        ----------
        x: int
            shift in pixels along the x-axis relative to the corresponding
            site of the reference cycle
            (positive value -> right, negative value -> left)
        y: int
            shift in pixels along the y-axis relative to the corresponding
            site of the reference cycle
            (positive value -> down, negative value -> up)
        site_id: int
            ID of the parent :class:`Site <tmlib.models.site.Site>`
        cycle_id: int
            ID of the parent :class:`Cycle <tmlib.models.cycle.Cycle>`
        '''
        self.x = x
        self.y = y
        self.site_id = site_id
        self.cycle_id = cycle_id

    def __repr__(self):
        return (
            '<SiteShift(id=%r, y=%r, x=%r)>'
            % (self.id, self.y, self.x)
        )
