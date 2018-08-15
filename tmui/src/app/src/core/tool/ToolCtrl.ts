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
/**
 * The base class for all tool controllers (i.e. angular controllers that are
 * created for the respective tool window).
 * The actual sendRequest method that will send its payload to the right server
 * route will be dynamically monkeypatched onto the controller object by the
 * tmToolWindow directive.
 * This method can't be marked abstract due to the way objects of this class
 * are created. 
 */
class ToolCtrl {
    sendRequest(payload: any): ng.IPromise<any> {
        return <ng.IPromise<any>>{};
    }
}

