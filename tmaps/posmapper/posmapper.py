_position_mappers = {}


def _get_position_mapper(format_id):
    """Get the position mapper function that
    was registered under id `format_id`"""
    if format_id in _position_mappers:
        return _position_mappers[format_id]
    else:
        raise Exception(
            'Mapper with id %s not registered!' % format_id)


def register_position_mapper(format_id):
    """A function decorator for registering functions that can be used
    to map coordinates to cell ids."""
    def mapper_dec(func):
        _position_mappers[format_id] = func
        return func
    return mapper_dec


def get_cell_at_pos(exp, x, y):
    """
    Get the cell id for the cell at position (x, y) for the experiment `exp`.

    If no cell was found, the `cell_id` in the returned dict will be None.
    If the position mapper returned the cell's center point or a polygonal
    cell outline, these values will be returned as well.

    The function to use when trying to find this cell id can be specified
    in the `expinfo.json` file. The config object under the key `position_mapper`
    is passed to the mapper that was registered under the given id.

    """
    # posmapper_settings = exp.posmapper_cfg # TODO: Consider removing

    # The id of the registered mapper that should be used
    # format_id = posmapper_settings.get('format_id', 'default') # TODO:

    # Information to pass to the mapper
    # mapper_config = posmapper_settings.get('config', {}) # TODO

    format_id = 'default' # TODO:
    # Retrieve the mapper and get the cell id
    mapping_func = _get_position_mapper(format_id)
    mapper_config = {}
    cell_id = mapping_func(exp, mapper_config, x, y)

    return cell_id
