function requireArg(options, optName) {
    if (_.isUndefined(options[optName])) {
        throw new Error('Function is missing argument with name "' + optName + '"!');
    }
}
