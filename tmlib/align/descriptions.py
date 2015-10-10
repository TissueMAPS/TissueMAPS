from cached_property import cached_property


class AlignmentDescription(object):

    '''
    Container for calculated shift and overhang values that can be used to
    align images between cycles.
    '''

    PERSISTENT = {'cycle_id', 'ref_cycle_id'}

    def __init__(self, description=None):
        self.description = description

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
        if not isinstance(value, int):
            raise TypeError(
                    'Attribute "cycle_id" must have type int')
        self._cycle_id = value

    @property
    def ref_cycle_id(self):
        '''
        Returns
        -------
        str
            identifier number of the corresponding reference cycle
        '''
        return self._ref_cycle_id

    @ref_cycle_id.setter
    def ref_cycle_id(self, value):
        if not(isinstance(value, int) or value is None):
            raise TypeError(
                    'Attribute "ref_cycle_id" must have type int')
        self._ref_cycle_id = value

    @property
    def overhang(self):
        '''
        Returns
        -------
        OverhangDescription
            overhang at each site of the image in pixels relative to the
            reference images 
        '''
        return self._overhang

    @overhang.setter
    def overhang(self, value):
        if not(isinstance(value, OverhangDescription) or value is None):
            raise TypeError(
                    'Attribute "overhangs" must have type OverhangDescription')
        self._overhang = value

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
            if attrib.startswith('_') or attrib.isupper():
                continue

            if attrib in self.PERSISTENT:
                description[attrib] = getattr(self, attrib)

            if attrib == 'shifts':
                description[attrib] = list()
                shifts = getattr(self, attrib)
                for i, sh in enumerate(shifts):
                    description[attrib].append(dict())
                    for a in dir(sh):
                        if a.startswith('_') or a.isupper():
                            continue
                        description[attrib][i][a] = getattr(sh, a)

            if attrib == 'overhang':
                description[attrib] = dict()
                oh = getattr(self, attrib)
                for a in dir(oh):
                    if a.startswith('_') or a.isupper():
                            continue
                    if a in oh.PERSISTENT:
                        description[attrib][a] = getattr(oh, a)

        return description

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


class OverhangDescription(object):

    '''
    Container for overhang values. These values represent the maximum shift
    values across all acquisition sites in each direction and are identical
    between all images of an experiment. 
    '''

    PERSISTENT = {'lower', 'upper', 'right', 'left'}

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

    PERSISTENT = {'site_id', 'x', 'y', 'is_above_max_shift'}

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
    def is_above_max_shift(self):
        '''
        Returns
        -------
        bool
            ``True`` when either `x` or `y` shift exceed
            `maximally_tolerated_shift` and ``False`` otherwise
        '''
        return self._is_above_max_shift

    @is_above_max_shift.setter
    def is_above_max_shift(self, value):
        if not isinstance(value, bool):
            raise TypeError(
                    'Attribute "is_above_max_shift" must have type bool')
        self._is_above_max_shift = value
