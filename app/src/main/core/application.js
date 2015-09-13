angular.module('tmaps.core')
.factory('application', ['$q', 'openlayers', 'AppInstanceFactory', '$state', 'ExperimentFactory',
    'AppInstanceDeserializer',
             function($q, ol, AppInstanceFactory, $state, ExperimentFactory, AppInstanceDeserializer) {

    function Application() {

        var isPhantom = /PhantomJS/.test(window.navigator.userAgent);
        if (!isPhantom && !ol.has.WEBGL) {
            throw new Error('TissueMAPS requires a browser supporting WebGL!');
        }

        this.viewportContainerId = 'viewports';
        this.activeInstanceNumber = 0;

        this.appInstances = [];

        var toolsDef = $q.defer();
        this.tools = toolsDef.promise;

        this.registerTools = function(toolArray) {
            toolsDef.resolve(toolArray);
        };
    }

    /**
     * Hide the whole viewport part of TissueMAPS.
     * Note that this will keep the active viewports. After calling
     * `showViewport` the state will be restored.
     * This function is called whenever the route sate changes away from the
     * visualization state.
     */
    Application.prototype.hideViewport = function() {
        $('.app').hide();
    };

    /**
     * Show the viewports after hiding them with `hideViewport`.
     */
    Application.prototype.showViewport = function() {
        $('.app').show();
        this.appInstances.forEach(function(inst) {
            inst.map.then(function(map) {
                map.updateSize();
            });
        });
    };

    Application.prototype.removeInstance = function(number) {
        this.appInstances[number].destroy();
        this.appInstances.splice(number, 1);
        if (number === this.activeInstanceNumber) {
            if (number >= 1) {
                // There are still instances with lower number
                this.setActiveInstanceByNumber(number - 1);
            } else if (this.appInstances.length > 0) {
                // There are still instance(s) with higher number
                this.setActiveInstanceByNumber(0);
            } else {
                // this was the last instance
            }
        }
    };

    Application.prototype.destroyAllInstances = function() {
        for (var i in this.appInstances) {
            this.appInstances[i].destroy();
            this.appInstances.splice(i, 1);
        }
        this.activeInstanceNumber = -1;
    };

    Application.prototype.setActiveInstanceByNumber = function(number) {
        var oldActive = this.getActiveInstance();
        this.activeInstanceNumber = number;
        var newActive = this.getActiveInstance();
        if (oldActive) {
            // If the instance wasn't deleted
            oldActive.setInactive();
        }
        newActive.setActive();
    };

    Application.prototype.setActiveInstance = function(instance) {
        var nr = this.appInstances.indexOf(instance);
        this.setActiveInstanceByNumber(nr);
    };

    Application.prototype.getInstanceByExpName = function(expName) {
        return _.find(this.appInstances, function(inst) {
            return inst.experiment.name === expName;
        });
    };

    Application.prototype.getInstanceById = function(id) {
        var inst = _.find(this.appInstances, function(inst) { return inst.id == id; });
        if (!inst) {
            throw new Error('No instance with id ' + id);
        } else {
            return inst;
        }
    };

    Application.prototype.getActiveInstance = function() {
        return this.appInstances[this.activeInstanceNumber];
    };

    Application.prototype.isActiveInstanceByIndex = function(index) {
        return index === this.activeInstanceNumber;
    };

    Application.prototype.isActiveInstanceById = function(id) {
        return this.getActiveInstance().id === id;
    };

    Application.prototype.addExperiment = function(experiment) {
        var exp = ExperimentFactory.create(experiment);
        var instance = AppInstanceFactory.create(exp);

        var layerOpts = _.partition(experiment.layers, function(opt) {
            return /_Mask/.test(opt.name);
        });

        var outlineOpts = layerOpts[0];
        var cycleOpts = layerOpts[1];

        instance.addChannelLayers(cycleOpts);
        instance.addMaskLayers(outlineOpts);

        this.appInstances.push(instance);
        if (this.appInstances.length === 1) {
            this.setActiveInstance(instance);
        }

        return instance;
    };

    Application.prototype.getToolById = function(id) {
        return this.tools.then(function(tools) {
            return _.find(tools, function(t) { return t.id === id; });
        });
    };

    Application.prototype.toBlueprint = function() {
        var self = this;

        var instanceBpPromises = _(this.appInstances).map(function(inst) {
            return inst.toBlueprint();
        });

        var appBpPromise = $q.all(instanceBpPromises)
        .then(function(instanceBps) {
            return {
                activeInstanceNumber: self.activeInstanceNumber,
                appInstances: instanceBps
            };
        });

        return appBpPromise;
    };

    Application.prototype.initFromBlueprint = function(bp) {
        this.destroyAllInstances();

        var self = this;
        var appInstancePromises = _(bp.appInstances).map(function(bp) {
            return AppInstanceDeserializer.deserialize(bp).then(function(inst) {
                inst.setInactive();
                self.appInstances.push(inst);
                return inst;
            });
        });
        $q.all(appInstancePromises).then(function(instances) {
            self.setActiveInstanceByNumber(bp.activeInstanceNumber);
        });
    };

    var app = new Application();
    return app;
}]);
