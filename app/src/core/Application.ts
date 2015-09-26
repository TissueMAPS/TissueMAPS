class Application {

    viewports: Viewport[] = [];

    private viewportContainerId = 'viewports';
    private activeViewportNumber = 0;

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
                private viewportDeserializer: ViewportDeserializer) {

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
        this.viewports.forEach((vp) => {
            vp.map.then(function(map) {
                map.updateSize();
            });
        });
    }

    removeViewport(num: number) {
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

    destroyAllViewports() {
        for (var i in this.viewports) {
            this.viewports[i].destroy();
            this.viewports.splice(i, 1);
        }
        this.activeViewportNumber = -1;
    }

    setActiveViewportByNumber(num: number) {
        var oldActive = this.getActiveViewport();
        this.activeViewportNumber = num;
        var newActive = this.getActiveViewport();
        if (oldActive) {
            // If the vp wasn't deleted
            oldActive.hide();
        }
        newActive.show();
    }

    setActiveViewport(vp: Viewport) {
        var nr = this.viewports.indexOf(vp);
        this.setActiveViewportByNumber(nr);
    }

    // TODO: Remove as many dependencies on this function as possible!
    // Widgets etc. should know the viewport they belong to.
    getActiveViewport(): Viewport {
        return this.viewports[this.activeViewportNumber];
    }

    addExperiment(experiment: ExperimentAPIObject) {
        // TODO: Depending on the experiment's type, create a different type of viewport.
        // TODO: Class viewport and experiment should be abstract.
        var exp = this.experimentFty.createFromServerResponse(experiment);
        var vp = this.viewportFty.create(exp);
        vp.initialize();

        this.viewports.push(vp);
        if (this.viewports.length === 1) {
            this.setActiveViewport(vp);
        }

        return vp;
    }

    serialize(): ng.IPromise<SerializedApplication> {
        var vpPromises = _(this.viewports).map((vp) => {
            return vp.serialize();
        });
        return this.$q.all(vpPromises).then((sers) => {
            var serApp =  {
                activeViewportNumber: this.activeViewportNumber,
                viewports: sers
            };
            return serApp;
        });
    }
}

angular.module('tmaps.core').service('application', Application);

interface SerializedApplication extends Serialized<Application> {
    activeViewportNumber: number;
    viewports: SerializedViewport[];
}
