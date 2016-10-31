// Copyright 2016 Markus D. Herrmann, University of Zurich and Robin Hafen
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
/// <reference path='../layer/ImageTileLayer.ts'/>
interface SerializedChannelLayer {
    id: string;
    tpoint: number;
    zplane: number;
    max_zoom: number;
    max_intensity: number;
    min_intensity: number;
    image_size: {
        width: number;
        height: number;
    };
}

interface ChannelLayerArgs {
    id: string;
    tpoint: number;
    zplane: number;
    maxZoom: number;
    maxIntensity: number;
    minIntensity: number;
    imageSize: Size;
    visible?: boolean;
}

class ChannelLayer extends ImageTileLayer {
    id: string;
    tpoint: number;
    zplane: number;
    maxIntensity: number;
    minIntensity: number;
    maxZoom: number;

    private _$stateParams: any;

    constructor(args: ChannelLayerArgs) {
        var _$stateParams = $injector.get<any>('$stateParams');
        var tileLayerArgs = {
            imageSize: args.imageSize,
            url: '/api/experiments/' + _$stateParams.experimentid +
                '/channel_layers/' + args.id + '',
            additiveBlend: true,
            visible: args.visible
        };
        super(tileLayerArgs);

        this.id = args.id;
        this.tpoint = args.tpoint;
        this.zplane = args.zplane;
        this.maxIntensity = args.maxIntensity;
        this.minIntensity = args.minIntensity;
        this.maxZoom = args.maxZoom;
    }
}
