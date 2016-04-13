var $injector;

describe('In Viewport', function() {
    // Load the module of ObjectLayer and its dependencies
    beforeEach(module('tmaps.core'));

    var viewer;

    // Injected services and factories
    var $httpBackend, $rootScope, $document, application;

    beforeEach(inject(function(_$httpBackend_, _$rootScope_,
        _$document_, _application_,
        _$injector_) {
        // Assign to variables
        $httpBackend = _$httpBackend_;
        $rootScope = _$rootScope_;
        $document = _$document_;
        application = _application_;
        $injector = _$injector_;
    }));

    beforeEach(function() {
        viewer = {};

        // Since our index isn't loaded and PhantomJS has its own document, we
        // need to append the necessary elements to it.
        $document.find('body').append('<div id="viewports"></div>');

        // Minimal viewport template
        var viewportTemplate =
            '<div class="instance-viewport">' +
                '<div class="map-container"></div>' +
            '</div>';

        $httpBackend.expectGET('/templates/main/viewport.html')
        .respond(200, viewportTemplate);
    });

    afterEach(function() {
        // Remove the added element again, otherwise each text will add a new
        // div.
        $('#viewports').remove();
    });


    var vp;

    beforeEach(function() {
        vp = new Viewport();
        vp.injectIntoDocumentAndAttach(viewer);
        // Perform requests for templates
        $httpBackend.flush();
    });

    describe('when creating the viewport', function() {

        it('a viewport container div should be added to the document', function() {
            var vpElements = $('#viewports > .instance-viewport');
            expect(vpElements.length).toEqual(1);
        });

        it('the openlayers map should be added into the document', function(done) {
            vp.map.then(function() {
                var olViewport = $('#viewports .instance-viewport .map-container .ol-viewport');
                expect(olViewport.length).toEqual(1);
                done();
            });
            // So the then callback on the $q deferred will fire.
            $rootScope.$apply();
        });

        it('the map property promise should get fulfilled', function(done) {
            vp.map.then(function(map) {
                expect(map).toBeDefined();
                done();
            });
            // So the then callback on the $q deferred will fire.
            $rootScope.$apply();
        });

        it('the element property promise should get fulfilled', function(done) {
            vp.element.then(function(scope) {
                expect(scope).toBeDefined();
                done();
            });
            // So the then callback on the $q deferred will fire.
            $rootScope.$apply();
        });

        it('the elementScope property promise should get fulfilled', function(done) {
            vp.elementScope.then(function(elementScope) {
                expect(elementScope).toBeDefined();
                done();
            });
            // So the then callback on the $q deferred will fire.
            $rootScope.$apply();
        });

        it('the viewport scope should receive the viewer as a property', function(done) {
            vp.elementScope.then(function(elementScope) {
                expect(elementScope.viewer).toEqual(viewer);
                done();
            });
            // So the then callback on the $q deferred will fire.
            $rootScope.$apply();
        });
    });

    describe('the function addObjectLayer', function() {
        pending();
        var l;

        beforeEach(function() {
            var options = {};
            l = new ObjectLayer('name', options);
        });

        it('should add an object layer to the viewport', function() {
            vp.addObjectLayer(l);

            expect(vp.objectLayers[0]).toEqual(l);
        });

        it('should add a vector layer to the openlayers map', function(done) {
            vp.addObjectLayer(l);

            vp.map.then(function(map) {
                expect(map.getLayers().getLength()).toEqual(1);
                done();
            });
            $rootScope.$apply();
        });
    });

    describe('the function removeObjectLayer', function() {
        pending();
        var l;

        beforeEach(function() {
            var options = {};
            l = new ObjectLayer('name', options);
            vp.addObjectLayer(l);
        });

        it('should remove an object layer from the viewport', function() {
            vp.removeObjectLayer(l);
            $rootScope.$apply();

            expect(vp.objectLayers.length).toEqual(0);
        });

        it('should remove a vector layer from the openlayers map', function() {
            vp.removeObjectLayer(l);

            vp.map.then(function(map) {
                expect(map.getLayers().getLength()).toEqual(0);
            });
            $rootScope.$apply();
        });
    });

    describe('the function addChannelLayer', function() {
        var l;
        var tileOpt;

        beforeEach(function() {
            tileOpt = {
                name: 'Test',
                imageSize: [123, 123],
                pyramidPath: '/experiments/D5YAKwe7/layers/Cell_Mask/'
            };
            l = new ChannelLayer(tileOpt);
        });

        it('should add a channel layer to the viewport', function() {
            vp.addChannelLayer(l);

            expect(vp.channelLayers[0].name).toEqual(l.name);
        });

        it('should add a tile layer to the openlayers map', function(done) {
            vp.addChannelLayer(l);

            vp.map.then(function(map) {
                expect(map.getLayers().getLength()).toEqual(1);
                done();
            });
            $rootScope.$apply();
        });

        it('should create a view if this is the first layer added', function(done) {
            vp.map.then(function(map) {
                expect(map.getView().getProjection().getCode()).not.toEqual('tm');
            });

            vp.addChannelLayer(l);

            vp.map.then(function(map) {
                expect(map.getView().getProjection().getCode()).toEqual('tm');
                done();
            });

            $rootScope.$apply();
        });
    });

    describe('the function removeChannelLayer', function() {
        var l;
        var tileOpt;

        beforeEach(function() {
            tileOpt = {
                name: 'Test',
                imageSize: [123, 123],
                pyramidPath: '/experiments/D5YAKwe7/layers/Cell_Mask/'
            };
            l = new ChannelLayer(tileOpt);
            vp.addChannelLayer(l);
        });

        it('removes a channel layer from the viewport', function() {
            vp.removeChannelLayer(l);

            expect(vp.channelLayers.length).toEqual(0);
        });

        it('removes the tile layer from the openlayers map', function(done) {
            vp.removeChannelLayer(l);

            vp.map.then(function(map) {
                expect(map.getLayers().getLength()).toEqual(0);
                done();
            });
            $rootScope.$apply();
        });
    });

    describe('the function destroy', function() {
        it('should remove the created scope', function() {
            vp.destroy();

            vp.elementScope.then(function(scope) {
                expect(scope.$$destroyed).toEqual(true);
            });
            $rootScope.$apply();
        });

        it('should remove the viewport from the document', function() {
            vp.destroy();
            $rootScope.$apply();

            var vpElements = $('#viewports > .instance-viewport');
            expect(vpElements.length).toEqual(0);
        });
    });

    describe('the function hide', function() {
        it('should hide the viewport', function() {
            vp.hide();
            $rootScope.$apply();

            var vpElements = $('#viewports > .instance-viewport');
            expect(vpElements.css('display')).toEqual('none');
        });
    });

    describe('the function show', function() {
        it('should show the viewport', function() {
            vp.hide();
            vp.show();
            $rootScope.$apply();

            var vpElements = $('#viewports > .instance-viewport');
            expect(vpElements.css('display')).toEqual('block');
        });

        it('should recalculate the map\'s size', function(done) {
            vp.map.then(function(map) {
                map.updateSize = jasmine.createSpy('updateSize');
            });
            $rootScope.$apply();

            vp.show();
            $rootScope.$apply();

            vp.map.then(function(map) {
                expect(map.updateSize).toHaveBeenCalled();
                done();
            });
            $rootScope.$apply();
        });
    });

    describe('the function serialize', function() {
        it('should save all the layers\' state', function(done) {
            var red = Color.RED;
            // Create a channel layer with some additional properties
            var tileOpt = {
                name: 'Test', imageSize: [123, 123],
                pyramidPath: '/experiments/D5YAKwe7/layers/Cell_Mask/',
                max: 0.5, min: 0.1, color: red
            };
            var l = new ChannelLayer(tileOpt);
            vp.addChannelLayer(l);

            var serializedVp = vp.serialize();

            serializedVp.then(function(ser) {
                expect(ser.channelLayerOptions).toBeDefined();

                var lopt = ser.channelLayerOptions[0]

                expect(lopt.name).toEqual(l.name);
                expect(lopt.pyramidPath).toEqual(l.pyramidPath);
                expect(lopt.imageSize).toEqual(l.imageSize);
                expect(lopt.max).toEqual(l.max);
                expect(lopt.min).toEqual(l.min);
                expect(red.equals(lopt.color)).toEqual(true);
                done();
            });

            $rootScope.$apply();
        });

        it('should save the map state', function(done) {
            vp.map.then(function(map) {
                var v = map.getView();
                v.setCenter([0, 0]);
                v.setResolution(2);
                v.setRotation(0);
                v.setZoom(0);
            });

            var serializedVp = vp.serialize();

            serializedVp.then(function(ser) {
                expect(ser.mapState).toBeDefined();

                vp.map.then(function(map) {
                    var v = map.getView();
                    var mapst = ser.mapState;

                    expect(mapst.zoom).toBeDefined();
                    expect(mapst.zoom).toEqual(v.getZoom());

                    expect(mapst.center).toBeDefined();
                    expect(mapst.center).toEqual(v.getCenter());

                    expect(mapst.resolution).toBeDefined()
                    expect(mapst.resolution).toEqual(v.getResolution());

                    done();
                });
            });

            $rootScope.$apply();
        });
    });

    describe('the function goToMapObject', function() {
        it('should move the current view to the given map object', function() {
            var middle = [50, -50];
            var outline = [
                [0, 0],
                [100, 0],
                [100, -100],
                [0, -100],
                [0, 0]
            ];
            var o = new MapObject(0, 'cell', 'polygon', {
                coordinates: outline
            });
            vp.goToMapObject(o);
            vp.map.then(function(map) {
                var v = map.getView();
                expect(v.fit).toBeDefined(); // has to be the right ol version
                expect(v.getCenter()).toEqual(middle);
            });
            $rootScope.$apply();
        });
    });
});
