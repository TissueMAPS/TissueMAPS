// (function() {

//     var fakeGetStatesResponse = {"owned":[{"id":"D5YAKwe7","name":"Nice findings","owner":"testuser","isSnapshot":false,"blueprint":"{\"bla\": 123}","$$hashKey":"object:27"},{"id":"K4NrewXv","name":"adsf","owner":"testuser","isSnapshot":false,"blueprint":{"activeInstanceNumber":0,"viewports":[{"channelLayerOptions":[{"additiveBlend":true,"brightness":0,"color":[1,1,1],"drawBlackPixels":true,"drawWhitePixels":true,"imageSize":[30307,23020],"max":0.17254901960784313,"min":0,"name":"Channel_01","opacity":1,"pyramidPath":"/experiments/D5YAKwe7/layers/Channel_01/","visible":true},{"additiveBlend":true,"brightness":0,"color":[1,1,1],"drawBlackPixels":true,"drawWhitePixels":true,"imageSize":[30307,23020],"max":1,"min":0,"name":"Channel_02","opacity":1,"pyramidPath":"/experiments/D5YAKwe7/layers/Channel_02/","visible":false},{"additiveBlend":true,"brightness":0,"color":[1,1,1],"drawBlackPixels":true,"drawWhitePixels":true,"imageSize":[30307,23020],"max":1,"min":0,"name":"Channel_03","opacity":1,"pyramidPath":"/experiments/D5YAKwe7/layers/Channel_03/","visible":false},{"additiveBlend":true,"brightness":0,"color":[1,1,1],"drawBlackPixels":true,"drawWhitePixels":true,"imageSize":[30310,23028],"max":1,"min":0,"name":"outlines","opacity":1,"pyramidPath":"/experiments/D5YAKwe7/layers/outlines/","visible":false}],"experiment":{"description":"Very nice exp","id":"D5YAKwe7","name":"150316-30min-PBS"},"mapState":{"center":[11583.400512695316,-8455.06771850586],"resolution":1.84979248046875,"rotation":0,"zoom":6},"maskLayerOptions":[{"additiveBlend":false,"brightness":0,"color":[1,1,1],"drawBlackPixels":false,"drawWhitePixels":true,"imageSize":[30310,23028],"max":1,"min":0,"name":"Cell_Mask","opacity":1,"pyramidPath":"/experiments/D5YAKwe7/layers/Cell_Mask/","visible":true},{"additiveBlend":false,"brightness":0,"color":[1,1,1],"drawBlackPixels":false,"drawWhitePixels":true,"imageSize":[30310,23028],"max":1,"min":0,"name":"Nuclei_Mask","opacity":1,"pyramidPath":"/experiments/D5YAKwe7/layers/Nuclei_Mask/","visible":false}],"selectionHandler":{"activeSelectionId":1,"selections":[{"cells":{"7487":[11657.427803379416,-8192.591617292079],"7489":[11753.424449423466,-8110.71670583092],"7492":[11784.609345719868,-7980.455125393724],"7493":[11798.873291754562,-8356.296753187196],"7494":[11828.79438822447,-8221.066754829806],"7499":[11968.875229211513,-8008.193893008052]},"id":0},{"cells":{"7457":[11253.445429126581,-8150.563906923842],"7467":[11368.639649159886,-8086.023301278664],"7474":[11490.70435486945,-8143.833714503526],"7475":[11512.330831369909,-8268.910467855942],"7476":[11466.463311382879,-7992.714769520226],"7481":[11581.081258965489,-7991.361361910387],"7483":[11589.657619767366,-7824.338732995991]},"id":1}]}}]},"$$hashKey":"object:28"}],"shared":[{"id":"LkwJvwXR","name":"Some other findings by testuser2","owner":"testuser2","isSnapshot":false,"blueprint":"{\"bla\": 123}"}]};


//     angular.module('tmaps.mock.main.appstate')
//     .service('appstateService', ['$q', function($q) {

//         this.currentState = {};
//         this.lastSavedAt;

//         this.stateHasBeenSavedAlready = jasmine.createSpy('stateHasBeenSavedAlready');

//         this.getStates = jasmine.createSpy('getStates').and.callFake(function() {
//             var def = $q.defer();
//             def.resolve(fakeGetStatesResponse);
//             return def.promise;
//         });

//         angular.extend(this, jasmine.createSpyObj('appstateServiceMock', [
//             'loadState',
//             'loadStateFromId',
//             'loadSnapshotFromId',
//             'saveState',
//             'promptForSaveAs',
//             'saveStateAs',
//             'shareState',
//             'getLinkForSnapshot'
//         ]));
//         // this.loadState = jasmine.createSpy('loadState');
//         // this.loadStateFromId = jasmine.createSpy('loadStateFromId');

//     }]);

// }());
