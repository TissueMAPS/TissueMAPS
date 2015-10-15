

class AlignmentDescription(object):

    '''
    Container for calculated shift and overhang values that can be used to
    align images between cycles.
    '''

    PERSISTENT = {'cycle_ix', 'ref_cycle_ix', 'overhang', 'shift'}

    def __init__(self, description=None):
        self.description = description

    @property
    def cycle_ix(self):
        '''
        Returns
        -------
        str
            identifier number of the corresponding target cycle
        '''
        return self._cycle_ix

    @cycle_ix.setter
    def cycle_ix(self, value):
        if not isinstance(value, int):
            raise TypeError(
                    'Attribute "cycle_ix" must have type int')
        self._cycle_ix = value

    @property
    def ref_cycle_ix(self):
        '''
        Returns
        -------
        str
            identifier number of the corresponding reference cycle
        '''
        return self._ref_cycle_ix

    @ref_cycle_ix.setter
    def ref_cycle_ix(self, value):
        if not(isinstance(value, int) or value is None):
            raise TypeError(
                    'Attribute "ref_cycle_ix" must have type int')
        self._ref_cycle_ix = value

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
                    'Attribute "overhang" must have type OverhangDescription')
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
        if not all([isinstance(v, ShiftDescription) for v in value]):
            raise TypeError(
                    'Elements of attribute "shifts" must have type '
                    'ShiftDescription')
        self._shifts = value

    def __iter__(self):
        '''
        Convert the object to a dictionary.

        Returns
        -------
        dict
            alignment description as key-value pairs

        Raises
        ------
        AttributeError
            when instance doesn't have a required attribute
        '''
        for attr in dir(self):

            if attr == 'shifts':
                shift_description = list()
                shifts = getattr(self, attr)
                for i, sh in enumerate(shifts):
                    shift_description.append(dict())
                    for a in dir(sh):
                        if a in ShiftDescription.PERSISTENT:
                            shift_description[i][a] = getattr(sh, a)
                yield (attr, shift_description)

            elif attr == 'overhang':
                overhang_description = dict()
                oh = getattr(self, attr)
                for a in dir(oh):
                    if a.startswith('_') or a.isupper():
                            continue
                    if a in oh.PERSISTENT:
                        overhang_description[a] = getattr(oh, a)
                yield (attr, overhang_description)

            else:
                if attr in self.PERSISTENT:
                    yield (attr, getattr(self, attr))

    @staticmethod
    def set(description):
        '''
        Set attribute values based on a description provided as key-value pair
        mappings.

        Parameters
        ----------
        description: dict
            alignment descriptions

        Returns
        -------
        AlignmentDescription
        '''
        if 'shifts' not in description.keys():
            raise KeyError('Aligment description requires key "shifts"')
        if not isinstance(description['shifts'], list):
            raise TypeError('The value of "shifts" must have type list')
        if 'overhang' not in description.keys():
            raise KeyError('Aligment description requires key "overhang"')
        if not isinstance(description['overhang'], dict):
            raise TypeError('The value of "overhang" must have type dict')

        alignment = AlignmentDescription()
        for key, value in description.iteritems():
            if key == 'overhang':
                overhang = OverhangDescription()
                for k, v in value.iteritems():
                    if k in overhang.PERSISTENT:
                        setattr(overhang, k, v)
                setattr(alignment, 'overhang', overhang)

            elif key == 'shifts':
                shifts = list()
                for element in value:
                    shift = ShiftDescription()
                    for k, v in element.iteritems():
                        if k in shift.PERSISTENT:
                            setattr(shift, k, v)
                    shifts.append(shift)
                setattr(alignment, 'shifts', shifts)

            else:
                if value in alignment.PERSISTENT:
                    setattr(alignment, key, value)

        return alignment


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
            number of pixels to crop at the bottom of the image
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
            number of pixels to crop at the top of the image
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
            number of pixels to crop at the left side of the image
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
            number of pixels to crop at the right side of the image
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

    PERSISTENT = {'site_ix', 'x', 'y', 'is_above_limit'}

    @property
    def site_ix(self):
        '''
        Returns
        -------
        int
            one-based globally unique position identifier number
        '''
        return self._site_ix

    @site_ix.setter
    def site_ix(self, value):
        if not isinstance(value, int):
            raise TypeError(
                    'Attribute "site_ix" must have type int')
        self._site_ix = value

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
    def is_above_limit(self):
        '''
        Returns
        -------
        bool
            ``True`` when either `x` or `y` shift exceed
            `maximally_tolerated_shift` and ``False`` otherwise
        '''
        return self._is_above_limit

    @is_above_limit.setter
    def is_above_limit(self, value):
        if not isinstance(value, bool):
            raise TypeError(
                    'Attribute "is_above_limit" must have type bool')
        self._is_above_limit = value
