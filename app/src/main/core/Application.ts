class Application {

    viewportContainerId = 'viewports';
    activeViewportNumber = 0;
    viewports: Viewport[] = [];

    static $inject = [
        '$q',
        '$',
        'openlayers',
        'experimentFactory',
        'viewportFactory',
        'viewportDeserializer'
    ];

    constructor(private $q: ng.IQService,
                private $: JQueryStatic,
                private ol,
                private experimentFty: ExperimentFactory,
                private viewportFty: ViewportFactory,
                private appInstDeserializer: ViewportDeserializer) {

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
        this.viewports.forEach((inst) => {
            inst.map.then(function(map) {
                map.updateSize();
            });
        });
    }

    remove(num: number) {
        this.viewports[num].destroy();
        this.viewports.splice(num, 1);
        if (num === this.activeViewportNumber) {
            if (num >= 1) {
                // There are still vps with lower number
                this.setActiveViewportByNumber(num - 1);
            } else if (this.viewports.length > 0) {
                // There are still vp(s) with higher number
                this.setActiveViewportByNumber(0);
            } else {
                // this was the last vp
            }
        }
    }

    destroyAlls() {
        for (var i in this.viewports) {
            this.viewports[i].destroy();
            this.viewports.splice(i, 1);
        }
        this.activeViewportNumber = -1;
    }

    setActiveViewportByNumber(num: number) {
        var oldActive = this.getActive();
        this.activeViewportNumber = num;
        var newActive = this.getActive();
        if (oldActive) {
            // If the vp wasn't deleted
            oldActive.setInactive();
        }
        newActive.setActive();
    }

    setActive(vp: Viewport) {
        var nr = this.viewports.indexOf(vp);
        this.setActiveViewportByNumber(nr);
    }

    getByExpName(expName: string): Viewport {
        return _.find(this.viewports, function(inst) {
            return inst.experiment.name === expName;
        });
    }

    getActive(): Viewport {
        return this.viewports[this.activeViewportNumber];
    }

    addExperiment(experiment: ExperimentAPIObject) {
        var exp = this.experimentFty.createFromServerResponse(experiment);
        var vp = this.viewportFty.create(exp);

        var layerOpts = _.partition(experiment.layers, function(opt) {
            return /_Mask/.test(opt.name);
        });

        var outlineOpts = layerOpts[0];
        var cycleOpts = layerOpts[1];

        vp.addChannelLayers(cycleOpts);
        vp.addMaskLayers(outlineOpts);

        this.viewports.push(vp);
        if (this.viewports.length === 1) {
            this.setActive(vp);
        }

        return vp;
    }

    serialize(): ng.IPromise<SerializedApplication> {
        var instPromises = _(this.viewports).map((inst) => {
            return inst.serialize();
        });
        return this.$q.all(instPromises).then((sers) => {
            var serApp =  {
                activeViewportNumber: this.activeViewportNumber,
                viewports: sers
            };
            console.log(serApp);
            return serApp;
        });
    }
}

angular.module('tmaps.core').service('application', Application);

interface SerializedApplication extends Serialized<Application> {
    activeViewportNumber: number;
    viewports: SerializedViewport[];
}
