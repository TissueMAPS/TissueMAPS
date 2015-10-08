from cached_property import cached_property


class AlignmentDescription(object):

    '''
    Container for calculated shift and overhang values that can be used to
    align images between cycles.
    '''

    def __init__(self, description=None):
        self.description = description

    # TODO: prevent setting additional attributes: __slot__ or __setattr__??

    @property
    def cycle_id(self):
        '''
        Returns
        -------
        str
            identifier number of the corresponding target cycle
        '''
        return self._cycle_id

    @cycle_id.setter
    def cycle_id(self, value):
        if not(isinstance(value, int) or value is None):
            raise TypeError(
                    'Attribute "cycle_id" must have type int')
        self._cycle_id = value

    @property
    def reference_cycle_id(self):
        '''
        Returns
        -------
        str
            identifier number of the corresponding reference cycle
        '''
        return self._reference_cycle_name

    @reference_cycle_id.setter
    def reference_cycle_id(self, value):
        if not(isinstance(value, int) or value is None):
            raise TypeError(
                    'Attribute "reference_cycle_id" must have type int')
        self._reference_cycle_id = value

    @cached_property
    def site_ids(self):
        '''
        Returns
        -------
        Set[int]
            site identifier numbers, for which shift values are available
        '''
        self._site_ids = set([s.id for s in self.shifts])
        return self._site_ids

    @property
    def max_tolerated_shift(self):
        '''
        Returns
        -------
        int
            maximally tolerated shift values in pixels (setting this value
            helps preventing artifacts, e.g. when empty images containing only
            Gaussian noise are registered)
        '''
        return self._max_tolerated_shift

    @max_tolerated_shift.setter
    def max_tolerated_shift(self, value):
        if not(isinstance(value, int) or value is None):
            raise TypeError(
                    'Attribute "max_tolerated_shift" must have type int')
        self._max_tolerated_shift = value

    @property
    def overhangs(self):
        '''
        Returns
        -------
        OverhangDescription
        '''
        return self._overhangs

    @overhangs.setter
    def overhangs(self, value):
        if not(isinstance(value, OverhangDesciption) or value is None):
            raise TypeError(
                    'Attribute "overhangs" must have type OverhangDescription')
        self._overhangs = value

    @property
    def shifts(self):
        '''
        Returns
        -------
        List[ShiftDescription]
        '''
        return self._shifts

    @shifts.setter
    def shifts(self, value):
        if not(isinstance(value, list) or value is None):
            raise TypeError(
                    'Attribute "shifts" must have type list')
        if not all([isinstance(v, OverhangDesciption) for v in value]):
            raise TypeError(
                    'Elements of attribute "shifts" must have type '
                    'OverhangDescription')
        self._shifts = value

    def serialize(self):
        '''
        Serialize attributes to description in form of key-value pair mappings.

        Returns
        -------
        description: dict
            alignment descriptions
        '''
        description = dict()
        for attrib in dir(self):
            if attrib.startswith('_'):
                continue
            if attrib == 'shifts':
                description[attrib] = list()
                for i, shifts in enumerate(attrib):
                    description[attrib].append(dict())
                    for shift_attrib in dir(shifts):
                        if shift_attrib.startswith('_'):
                            continue
                        description[attrib][i][shift_attrib] = \
                            getattr(shifts, shift_attrib)
            if attrib == 'overhangs':
                description[attrib] = dict()
                for overhang_attrib in dir(attrib):
                    if overhang_attrib.startswith('_'):
                            continue
                    description[attrib][overhang_attrib] = \
                        getattr(self, overhang_attrib)
            description[attrib] = getattr(self, attrib)

    def set(self, description):
        '''
        Set attribute values based on a description provided as key-value pair
        mappings.

        Parameters
        ----------
        description: dict
            alignment descriptions
        '''
        if 'shifts' not in description.keys():
            raise KeyError('Aligment description requires key "shifts"')
        if not isinstance(description['shifts'], list):
            raise TypeError('The value of "shifts" must have type list')
        if 'overhangs' not in description.keys():
            raise KeyError('Aligment description requires key "overhangs"')
        if not isinstance(description['overhangs'], dict):
            raise TypeError('The value of "overhangs" must have type dict')

        overhang_description = OverhangDesciption()
        for k, v in description['overhangs'].iteritems():
            setattr(overhang_description, k, v)
        setattr(self, 'overhangs', overhang_description)

        shift_descriptions = list()
        for s in description['shifts']:
            shift = ShiftDescription()
            for k, v in s.iteritems():
                setattr(shift, k, v)
            shift_descriptions.append(shift)
        setattr(self, 'shifts', shift_descriptions)


class OverhangDesciption(object):

    '''
    Container for overhang values. These values represent the maximum shift
    values across all acquisition sites in each direction and are identical
    between all images of an experiment. 
    '''

    @property
    def lower(self):
        '''
        Returns
        -------
        int
            overhang in pixels at the lower side of the image
            relative to its reference:
            pixels to crop at the bottom of the image
        '''
        return self._lower

    @lower.setter
    def lower(self, value):
        if not isinstance(value, int):
            raise TypeError(
                    'Attribute "lower" must have type int')
        self._lower = value

    @property
    def upper(self):
        '''
        Returns
        -------
        int
            overhang in pixels at the upper side of the image
            relative to its reference:
            pixels to crop at the top of the image
        '''
        return self._upper

    @upper.setter
    def upper(self, value):
        if not isinstance(value, int):
            raise TypeError(
                    'Attribute "upper" must have type int')
        self._upper = value

    @property
    def left(self):
        '''
        Returns
        -------
        int
            overhang in pixels at the left side of the image relative
            to its reference:
            pixels to crop at the left side of the image
        '''
        return self._left

    @left.setter
    def left(self, value):
        if not isinstance(value, int):
            raise TypeError(
                    'Attribute "left" must have type int')
        self._left = value

    @property
    def right(self):
        '''
        Returns
        -------
        int
            overhang in pixels at the right side of the image relative
            to its reference:
            pixels to crop at the right side of the image
        '''
        return self._right

    @right.setter
    def right(self, value):
        if not isinstance(value, int):
            raise TypeError(
                    'Attribute "right" must have type int')
        self._right = value


class ShiftDescription(object):

    '''
    Container for shift values. These values represent the shift in pixels
    for an individual acquisition site in y (vertical) and x (horizontal)
    direction relative to a reference image acquired at the same site.
    They can differ between images of an experiment and are zero
    for images of the reference cycle.
    '''

    @property
    def site_id(self):
        '''
        Returns
        -------
        int
            one-based globally unique position identifier number
        '''
        return self._site_id

    @site_id.setter
    def site_id(self, value):
        if not isinstance(value, int):
            raise TypeError(
                    'Attribute "site_id" must have type int')
        self._site_id = value

    @property
    def x(self):
        '''
        Returns
        -------
        int
            shift of the image in pixels in x direction relative to its
            reference (positive value -> to the left; negative value -> to the
            right)
        '''
        return self._x

    @x.setter
    def x(self, value):
        if not isinstance(value, int):
            raise TypeError(
                    'Attribute "x" must have type int')
        self._x = value

    @property
    def y(self):
        '''
        Returns
        -------
        int
            shift of the image in pixels in y direction relative to its
            reference (positive value -> downwards; negative value -> upwards)
        '''
        return self._y

    @y.setter
    def y(self, value):
        if not isinstance(value, int):
            raise TypeError(
                    'Attribute "y" must have type int')
        self._y = value

    @property
    def exceeds_max_shift(self):
        '''
        Returns
        -------
        bool
            ``True`` when either `x` or `y` shift exceed
            `maximally_tolerated_shift` and ``False`` otherwise
        '''
        return self._exceeds_max_shift

    @exceeds_max_shift.setter
    def exceeds_max_shift(self, value):
        if not isinstance(value, bool):
            raise TypeError(
                    'Attribute "exceeds_max_shift" must have type bool')
        self._exceeds_max_shift = value
