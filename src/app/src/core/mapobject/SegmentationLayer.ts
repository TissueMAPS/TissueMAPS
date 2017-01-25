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
/// <reference path='../layer/VectorTileLayer.ts'/>

interface SegmentationLayerArgs {
    id: string;
    tpoint: number;
    zplane: number;
    size: Size;
    visible?: boolean;
}

class SegmentationLayer extends VectorTileLayer {

    id: string;

    /**
     * Construct a SegmentationLayer.
     * @classdesc A layer showing outlines for a specific mapobject type.
     */
    constructor(args: SegmentationLayerArgs) {

        var _$stateParams = $injector.get<any>('$stateParams');
        var url = '/api/experiments/' + _$stateParams.experimentid +
                  '/segmentation_layers/' + args.id +
                  '/tiles?x={x}&y={y}&z={z}';
        super({
            visible: args.visible,
            size: args.size,
            url: url,
            strokeColor: Color.WHITE,
            fillColor: Color.WHITE.withAlpha(0),
        });

        this.id = args.id;
    }
}


