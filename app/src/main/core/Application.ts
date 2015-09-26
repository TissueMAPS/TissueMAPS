class Application {

    viewportContainerId = 'viewports';
    activeInstanceNumber = 0;
    appInstances: AppInstance[] = [];

    static $inject = [
        '$q',
        '$',
        'openlayers',
        'experimentFactory',
        'appInstanceFactory',
        'appInstanceDeserializer'
    ];

    constructor(private $q: ng.IQService,
                private $: JQueryStatic,
                private ol,
                private experimentFty: ExperimentFactory,
                private appInstFty: AppInstanceFactory,
                private appInstDeserializer: AppInstanceDeserializer) {

        // Check if the executing browser is PhantomJS (= code runs in
        // testing mode.
        var isPhantom = /PhantomJS/.test(window.navigator.userAgent);
        if (!isPhantom && !ol.has.WEBGL) {
            throw new Error('TissueMAPS requires a browser supporting WebGL!');
        }
    }

    /**
     * Hide the whole viewport part of TissueMAPS.
     * Note that this will keep the active viewports. After calling
     * `showViewport` the state will be restored.
     * This function is called whenever the route sate changes away from the
     * visualization state.
     */
    hideViewports() {
        this.$('.app').hide();
    }

    /**
     * Show the viewports after hiding them with `hideViewports`.
     */
    showViewports() {
        this.$('.app').show();
        this.appInstances.forEach((inst) => {
            inst.map.then(function(map) {
                map.updateSize();
            });
        });
    }

    removeInstance(num: number) {
        this.appInstances[num].destroy();
        this.appInstances.splice(num, 1);
        if (num === this.activeInstanceNumber) {
            if (num >= 1) {
                // There are still instances with lower number
                this.setActiveInstanceByNumber(num - 1);
            } else if (this.appInstances.length > 0) {
                // There are still instance(s) with higher number
                this.setActiveInstanceByNumber(0);
            } else {
                // this was the last instance
            }
        }
    }

    destroyAllInstances() {
        for (var i in this.appInstances) {
            this.appInstances[i].destroy();
            this.appInstances.splice(i, 1);
        }
        this.activeInstanceNumber = -1;
    }

    setActiveInstanceByNumber(num: number) {
        var oldActive = this.getActiveInstance();
        this.activeInstanceNumber = num;
        var newActive = this.getActiveInstance();
        if (oldActive) {
            // If the instance wasn't deleted
            oldActive.setInactive();
        }
        newActive.setActive();
    }

    setActiveInstance(instance: AppInstance) {
        var nr = this.appInstances.indexOf(instance);
        this.setActiveInstanceByNumber(nr);
    }

    getInstanceByExpName(expName: string): AppInstance {
        return _.find(this.appInstances, function(inst) {
            return inst.experiment.name === expName;
        });
    }

    getActiveInstance(): AppInstance {
        return this.appInstances[this.activeInstanceNumber];
    }

    addExperiment(experiment: ExperimentAPIObject) {
        var exp = this.experimentFty.createFromServerResponse(experiment);
        var instance = this.appInstFty.create(exp);

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
    }

    serialize(): ng.IPromise<SerializedApplication> {
        var instPromises = _(this.appInstances).map((inst) => {
            return inst.serialize();
        });
        return this.$q.all(instPromises).then((serInstances) => {
            var serApp =  {
                activeInstanceNumber: this.activeInstanceNumber,
                appInstances: serInstances
            };
            console.log(serApp);
            return serApp;
        });
    }
}

angular.module('tmaps.core').service('application', Application);

interface SerializedApplication extends Serialized<Application> {
    activeInstanceNumber: number;
    appInstances: SerializedAppInstance[];
}
