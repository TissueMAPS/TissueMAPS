function CutMask = PerimeterWatershedSegmentation(LabelImage,IntensityImage,PerimeterTrace,MaxEqivRadius,MinEquivAngle,ObjSizeThres,numRegionThreshold,varargin)
%PERIMETERWATERSHEDSEGMENTATION separates clumped objects along watershed
%lines between concave regions.
%
%   CUTMASK=PERIMETERWATERSHEDSEGMENTATION(LABELIMAGE,INTENSITYIMAGE,PERIMETERTRACE,MAXEQIVRADIUS,MINEQIVANGLE,OBJSIZETHRES,NUMREGIONTHRESHOLD)
%   separates objects in LABELIMAGE along watershed lines determined in INTENSITYIMAGE
%   between concave regions specified by PERIMETERTRACE. Note that all image operations
%   are carried out on small 'mini' images the size of each object's bounding box.
%   This approach dramatically reduces computation time!
%
%   LABELIMAGE is a labeled image (output of bwlabel.m) containing the objects
%   that should be separated.
%
%   INTENSITYIMAGE is a grayscale image of class 'double' of the same size as LABELIMAGE.
%
%   PERIMETERTRACE is a cell array of curvature measurements (output of PerimeterAnalysis.m)
%   for each object in LABELIMAGE.
%
%   MAXEQIVRADIUS and MINEQIVANGLE are the maximal equivalent radius and the minimal equivalent
%   angle concave regions should have to be eligible for cutting.
%   For details see IdentifyPrimaryIterative.m and PerimeterAnalysis.m.
%
%   OBJSIZETHRES is the minimal size cut objects should have. Potential cut lines
%   will be discarded in case the resulting objects would fall below this threshold.
%
%   NUMREGIONTHRESHOLD is the maximally allowed number of concave regions.
%   Objects that have more concave regions than this value are not processed!
%
%   Optional input arguments: 'debugON' command results in the display of all intermediate
%   processing steps (selected pixels within concave regions -> green points,
%   selected watershed nodes -> red points, selected watershed lines -> yellow lines)
%   on the intensity image of each object.
%
%
%   Authors:
%       Markus Herrmann
%       Nicolas Battich
%
%   (c) Pelkmans Lab 2013

% Obtain pixels at inner periphery of objects
props = regionprops(LabelImage,'BoundingBox');
BoxPerObj = cat(1,props.BoundingBox);

if all(size(BoxPerObj)==0) % this can sometimes happen
    CutMask = zeros(size(LabelImage));
    return
end

% Calculate allowed coordinates per object
% -> recalculating objects is necessary because of a background bug!
ObjectIDs = setdiff(unique(LabelImage(:)),0);

% Get outer coordinates of bounding box of each object
distanceToObjectMax = 3;
N = floor(BoxPerObj(:,2)-distanceToObjectMax-1);                    f = N < 1;                            N(f) = 1;
S = ceil(BoxPerObj(:,2)+BoxPerObj(:,4)+distanceToObjectMax+1);      f = S > size(LabelImage,1);           S(f) = size(LabelImage,1);
W = floor(BoxPerObj(:,1)-distanceToObjectMax-1);                    f = W < 1;                            W(f) = 1;
E = ceil(BoxPerObj(:,1)+BoxPerObj(:,3)+distanceToObjectMax+1);      f = E > size(LabelImage,2);           E(f) = size(LabelImage,2);

CutMask  = zeros(size(LabelImage));

%=============debug=============
% set up debug mode
if strcmpi(varargin,'debugON')
    debug = true;
    figure
    h=gcf;
%     dbclear in PerimeterWatershedSegmentation
%     dbstop in PerimeterWatershedSegmentation.m at 270
%     dbstop in PerimeterWatershedSegmentation.m at 287
%     dbstop in PerimeterWatershedSegmentation.m at 521
%     dbstop in PerimeterWatershedSegmentation.m at 573
else
    debug = false;
end
%===========debug-end===========

if ~isempty(ObjectIDs)
    clear i;
    for i = 1:length(ObjectIDs)

        clear SelectedLines;

        %% Load concave regions for current object
        CurrentPreimProps = PerimeterTrace{i};
        ConcaveRegions = bwlabel((CurrentPreimProps(:,11)==-1));
        numConcave = length(setdiff(unique(ConcaveRegions),0));
        propsConcaveRegion = zeros(numConcave,12,'double');  % summary of properties for each concave region:
        pixelsConcaveRegions = cell(numConcave,1);

        %% Characterize concave regions of current object
        for j = 1:numConcave
            propsCurrentRegion = CurrentPreimProps(ConcaveRegions==j,:);
            NormalVectors = propsCurrentRegion(:,3:4);
            NormCurvature = propsCurrentRegion(:,9);
            propsConcaveRegion(j,1) = max(NormCurvature);
            propsConcaveRegion(j,2) = mean(NormCurvature);
            MaximaIndices = (NormCurvature==propsConcaveRegion(j,1));  % indices of pixels where the curvature is maximal
            propsConcaveRegion(j,3:4) = mean(NormalVectors(MaximaIndices,:),1);  % normal vector at pixels where the norm of the curvature is maximal (the maximum may apper multiple times in few cases ->mean)
            propsConcaveRegion(j,5:6) = mean(NormalVectors,1);  % mean normal vector
            FirstMaximumIndex = find(MaximaIndices,1,'first');
            LastMaximumIndex = find(MaximaIndices,1,'last');
            MeanMaximumIndex = round((LastMaximumIndex+FirstMaximumIndex)/2);%index of the pixel at which the curvature is maximal, if there are more than one maxima, a pixel inbetween the maxima is picked.
            propsConcaveRegion(j,7:8) = propsCurrentRegion(MeanMaximumIndex,1:2);%pixel coordinates of maximum curvature, or mean between maxima
            propsConcaveRegion(j,9:10) = propsCurrentRegion(round((size(propsCurrentRegion,1)+1)/2),1:2);%center pixel
            %The sum of curvature has a maximum of 2*pi (object shape=circle)
            %exceptions are very small object sizes or very large objects in
            %combination with a too small sliding window (eg window<r/15)
            %the total curvature is the equivalent angle (radian) of the curve!!!
            propsConcaveRegion(j,11) = sum(NormCurvature);%total curvature of region = EQUIVALENT ANGLE of circle segment
            propsConcaveRegion(j,12) = length(NormCurvature)/sum(NormCurvature);%EQUIVALENT RADIUS
            propsConcaveRegion(j,13) = j;%save region ID so we can later quickly refer to information in CurrentPreimProps (see start of loop)
            pixelsConcaveRegions{j} = propsCurrentRegion(:,1:2);
        end

        if size(propsConcaveRegion, 1) > numRegionThreshold
            fprintf('%s: object # %d skipped because it has too many concave regions\n', mfilename, i)
            continue
        end

        %% Select concave regions meeting the Radius/Angle criteria
        QualifyingRegionsMask = (propsConcaveRegion(:,11)>=MinEquivAngle) & (propsConcaveRegion(:,12)<=MaxEqivRadius);%0.1, 30
        SelectedRegions = propsConcaveRegion(QualifyingRegionsMask,:);

        %% Define cut points
        % use only the pixels of the concave regions with mean/max gradient
        %CutCoordList = SelectedRegions(:,[9,10]);%mean gradient of regions
        CutCoordList = SelectedRegions(:,[7,8]);%maximum gradient of regions
        regionIndex = (1:length(CutCoordList))';

% ======================================================================================================================================
% === object image -- start ==============================================================================================================

        if size(CutCoordList,1)>1

            %% Get small cropped versions of image region containing the object

            %%% Map CutCoordList
            % (follow the reverse strategy as below for mapping back)
            rCut = CutCoordList(:,1)+1-N(i);
            cCut = CutCoordList(:,2)+1-W(i);
            miniCutCoordList = [rCut,cCut];

            %%% Create mini images
            imMini = LabelImage(N(i):S(i),W(i):E(i));
            imBwMini = imMini==i;
            %figure,imagesc(imBwMini)
            imIntMini = IntensityImage(N(i):S(i),W(i):E(i));
            imIntMini(~imBwMini) = 0;%NaN
            %figure,imagesc(imIntMini)

            %%% Pad
            padSize = [1 1];
            padbw = padarray(imBwMini,padSize);
            padInt = padarray(imIntMini,padSize);

            %% Identify watershed lines and nodes

            %%% Get watershed transform
            padws = double(watershed(imcomplement(padInt)));
            padws(~logical(padbw)) = 0;
            %figure,imagesc(padws)

            %%% Get watershed lines
            imCurrentPreLines = zeros(size(padInt));
            imCurrentPreLines(~padws) = padbw(~padws);
            imCurrentPreLines(~padbw) = 0;
            %figure,imagesc(imCurrentPreLines)

            %%% Define lines and crossing points
            imCurrentPreLines2 = imCurrentPreLines;
            imCurrentPreLines2(~padbw) = 5;
            f = [0 1 0; 1 0 1; 0 1 0;];
            imCurrentLinesAndNodes = imfilter(imCurrentPreLines2,f);
            imCurrentLinesAndNodes(~imCurrentPreLines2) = 0;
            imCurrentLinesAndNodes(~padbw) = 0;
            %figure;imagesc(imCurrentLinesAndNodes)

            %%% Define lines and measure area
            imCurrentLines = bwlabel(imCurrentLinesAndNodes<3 & imCurrentLinesAndNodes>0,4);
            %figure, imagesc(imCurrentLines)

            LineAreas = regionprops(imCurrentLines,'area');
            LineAreas = cat(1,LineAreas(:).Area);
            LineIds = unique(imCurrentLines(:));
            LineIds(LineIds==0) = [];

            %%% Define nodes and measure their centroids
            imCurrentNodes = bwlabel(imCurrentLinesAndNodes>2,4);
            NodesCentroids = regionprops(imCurrentNodes,'centroid');
            NodesCentroids = cat(1,NodesCentroids(:).Centroid);
            NodesIds = unique(imCurrentNodes(:));
            NodesIds = NodesIds(2:end)';
            %figure, imagesc(imCurrentNodes)

            %%% Build connection matrix used to measure paths
            f = {[0 1 0; 0 0 0; 0 0 0;] [0 0 0; 1 0 0; 0 0 0;] [0 0 0; 0 0 1; 0 0 0;] [0 0 0; 0 0 0; 0 1 0;]};
            DisplacedLines = cellfun(@(x) imfilter(imCurrentLines,x),f,'uniformoutput',false);%what are DisplacedLines?
            DisplacedLines = cat(3,DisplacedLines{:});

            NodeType = zeros(size(NodesIds));
            matNodesLines = zeros(length(NodesIds),length(LineAreas));
            for iNode = 1:length(NodesIds)
                tmpid = NodesIds(iNode);

                tmpix = imCurrentNodes==tmpid;
                temptype = unique(imCurrentLinesAndNodes(tmpix));
                NodeType(iNode) = max(temptype)>5;

                tmpix = repmat(tmpix(:),4,1);
                templineids = unique(DisplacedLines(tmpix));
                templineids(templineids==0) = [];
                matNodesLines(iNode,templineids') = templineids';
            end

            matNodesNodes = zeros(length(NodesIds));
            matNodesNodesLabel = zeros(length(NodesIds));
            for iNode = 1:length(NodesIds)
                tmplines = unique(matNodesLines(iNode,:));
                tmplines(tmplines==0) = [];
                for l = tmplines
                    tmpnodes = find(matNodesLines(:,l));
                    matNodesNodes(iNode,tmpnodes) = LineAreas(l);
                    matNodesNodesLabel(iNode,tmpnodes) = l;
                end

            end
            matNodesNodes(sub2ind([length(NodesIds) length(NodesIds)],NodesIds,NodesIds)) = 0;
            matNodesNodesLabel(sub2ind([length(NodesIds) length(NodesIds)],NodesIds,NodesIds)) = 0;


            %% Define border, source and target nodes

            %%% Determine border nodes
            NodeToTest = NodesIds(logical(NodeType));

            %=============debug=============
            if debug
                [I, J] = find(imCurrentLines>0);
                figure(h), imagesc(padInt)
                title(sprintf('Object # %d', i))
                colormap(gray)
                freezeColors
                hold on
                scatter(J, I, 150, 'y', 's', 'MarkerFaceColor','y')
                scatter(NodesCentroids(NodeToTest,1), NodesCentroids(NodeToTest,2), 2000, 'r', '.');
                hold off
                pause(1)
            end
            %===========debug-end===========

            %%% Determine which border nodes lie in closest proximity to potential cut points
            PotentialNodesCoordinates = NodesCentroids(NodeToTest,:);
            PotentialNodesCoordinates = round(PotentialNodesCoordinates);
            NodeCoordList = zeros(size(PotentialNodesCoordinates));
            if ~isempty(PotentialNodesCoordinates) && ~isempty(miniCutCoordList)

                AllLines = struct();

                NodeCoordList(:,1) = PotentialNodesCoordinates(:,2);
                NodeCoordList(:,2) = PotentialNodesCoordinates(:,1);

                % Calculate distances between potential cut points and nodes and determine closest nodes/cut points and the respective indexes
                [~,ClosestNodesIndex] = pdist2(NodeCoordList,miniCutCoordList,'euclidean','Smallest',3);
                ClosestNodesIndex = unique(ClosestNodesIndex(:));

                %=============debug=============
                if debug
                    % Display selected regions over intensity image
                    figure(h),imagesc(padInt)
                    title(sprintf('Object # %d', i))
                    colormap(gray)
                    hold on
                    scatter(miniCutCoordList(:,2), miniCutCoordList(:,1), 2000, 'g', '.');
                    hold off
                    pause(1)

                    % Display selected nodes over intensity image
                    SelectedNodeCoordList = NodeCoordList(ClosestNodesIndex,:);
                    figure(h),imagesc(padInt)
                    title(sprintf('Object # %d', i))
                    colormap(gray)
                    hold on
                    scatter(SelectedNodeCoordList(:,2), SelectedNodeCoordList(:,1), 2000, 'r', '.');
                    hold off
                    pause(1)
                end
                %===========debug-end===========

                if ~isempty(ClosestNodesIndex)

                    %%% Define source and target nodes
                    ClosestNodesIds = NodeToTest(ClosestNodesIndex);
                    NodeixS = repmat(ClosestNodesIds,length(ClosestNodesIds),1);
                    NodeixT = repmat(ClosestNodesIds,1,length(ClosestNodesIds));
                    NodeixS = NodeixS(:);
                    NodeixT = NodeixT(:);


                    %% Get watershed lines for cutting

                    %%% Get shortest paths between nodes
                    [dist,path] = cpsub.dijkstraCP(matNodesNodes>0,matNodesNodes,ClosestNodesIds,ClosestNodesIds);
                    dist = dist(:)';
                    QuantileDistance = quantile(dist(dist~=0 & dist~=Inf),1);
                    thrix = dist~=0 & dist<QuantileDistance;
                    NodeixS2 = NodeixS(thrix);
                    NodeixT2 = NodeixT(thrix);

                    %%% Get coordinates of source and target nodes
                    NodeSCoordList = NodesCentroids(NodeixS2,:);
                    NodeSCoordList = round(NodeSCoordList);
                    NodeTCoordList = NodesCentroids(NodeixT2,:);
                    NodeTCoordList = round(NodeTCoordList);

                    %%% Get index of cut points closest to source and target nodes, respectively (necessary to retrieve normal vectors)
                    [~,ClosestCutPointsSIndex] = pdist2(miniCutCoordList,fliplr(NodeSCoordList),'euclidean','Smallest',1);
                    ClosestCutPointsSIndex = ClosestCutPointsSIndex(:);
                    [~,ClosestCutPointsTIndex] = pdist2(miniCutCoordList,fliplr(NodeTCoordList),'euclidean','Smallest',1);
                    ClosestCutPointsTIndex = ClosestCutPointsTIndex(:);

                    AllLines = struct();

                    % ---------------------------------------------------------------------------------------------------------------------------------------
                    % ---- Bottleneck -- start ----------------------------------------------------------------------------------------------------------------
%                     tic

                    for n = 1:length(NodeixT2)

                        %%% Find path
                        tmppath = path{ClosestNodesIds==NodeixS2(n),ClosestNodesIds==NodeixT2(n)};
                        tmpImage = zeros(size(imCurrentNodes));
                        tmpImage(ismember(imCurrentNodes(:),tmppath(:))) = 1;

                        %%% Built path image
                        for j = 1:length(tmppath)-1
                            tmpImage(imCurrentLines==matNodesNodesLabel(tmppath(j),tmppath(j+1))) = 1;
                            %figure,imagesc(tmpImage)
                        end
                        %figure,imagesc(tmpImage)

%                         %=============debug=============
%                         if debug
%                             % Display current line over intensity image
%                             LineOverlay = padInt;
%                             LineOverlay(tmpImage>0) = quantile(padInt(:),0.998);
%                             figure(h),imagesc(LineOverlay), colormap('jet')
%                         end
%                         %===========debug-end===========


                        %% Simulate segmentation using watershed lines and characterize cut line and resulting objects

                        tmpSegmentation = padbw;
                        tmpSegmentation(tmpImage>0) = 0;
                        % Get size and shape properties of segmented objects
                        tmpSubSegmentation = bwconncomp(tmpSegmentation>0);
                        tmpNumObjects = tmpSubSegmentation.NumObjects;
                        tmpSubAreas = cell2mat(cellfun(@numel, tmpSubSegmentation.PixelIdxList,'UniformOutput',false));

                        if tmpNumObjects==2 && min(tmpSubAreas)>ObjSizeThres

                            % do not use line if segmentation would result
                            % in more than 2 objects or too small objects

                            %%% Get object measurements
                            tmpSubprops = regionprops(tmpSegmentation,'Solidity','Area','Perimeter');
                            tmpSubSolidity = cat(2,tmpSubprops.Solidity);
                            tmpSubAreas = cat(2,tmpSubprops.Area);
                            [~,ix] = min(tmpSubAreas);
                            tmpSubFormFactor = (log((4*pi*cat(1,tmpSubprops.Area)) ./ ((cat(1,tmpSubprops.Perimeter)+1).^2))*(-1))';%make values positive for easier interpretation of parameter values
                            % store measurements
                            AllLines(n).areasobj = tmpSubAreas;
                            AllLines(n).solobj = tmpSubSolidity;
                            AllLines(n).formobj = tmpSubFormFactor;
                            AllLines(n).lineimage = tmpImage;
                            AllLines(n).segmimage = tmpSegmentation;

                            %%% Get line measurements
                            % Intensity along the line
                            tmpintimage = tmpImage>0;
                            tmpMaxInt = max(padInt(tmpintimage));
                            tmpMeanInt = mean(padInt(tmpintimage));
                            tmpStdInt = std(padInt(tmpintimage));
                            tmpQuantInt = quantile(padInt(tmpintimage),0.75);
                            tmpLength = sum(tmpintimage(:));
                            % store measurements
                            AllLines(n).maxint = tmpMaxInt;
                            AllLines(n).meanint = tmpMeanInt;
                            AllLines(n).quantint = tmpQuantInt;
                            AllLines(n).stdint = tmpStdInt;
                            AllLines(n).length = tmpLength;

                            % Straightness of the line
                            tmpcentroid1 = round(NodesCentroids(ClosestNodesIds(ClosestNodesIds==NodeixS2(n)),:));%tmpcentroid1 = round(NodesCentroids(NodeToTest(NodeToTest==NodeixS2(n)),:));
                            tmpcentroid2 = round(NodesCentroids(ClosestNodesIds(ClosestNodesIds==NodeixT2(n)),:));
                            m = (tmpcentroid1(2)-tmpcentroid2(2))/(tmpcentroid1(1)-tmpcentroid2(1));
                            x = (min([tmpcentroid1(1),tmpcentroid2(1)]):max([tmpcentroid1(1),tmpcentroid2(1)]));
                            if m~=-Inf && m~=Inf && ~isnan(m)
                                y = (min([tmpcentroid1(2),tmpcentroid2(2)]):max([tmpcentroid1(2),tmpcentroid2(2)]));
                                c = tmpcentroid1(2)-m*tmpcentroid1(1);
                                py = round(m.*x+c);
                                px = round((y-c)/m);
                                if max(size(tmpImage,1)) > max([y py]) && max(size(tmpImage,2)) > max([px x])
                                    StraigtLineix = sub2ind(size(tmpImage),[y py],[px x]);
                                else
                                    StraigtLineix = NaN;
                                end
                            else
                                StraigtLineix = NaN;
                            end
                            tmprim = tmpImage;
                            tmprim(StraigtLineix(~isnan(StraigtLineix))) = 1;
                            tmprim = imfill(tmprim);
                            tmpRatio = sum(tmprim(:))/length(unique(StraigtLineix));
                            % store measurements
                            AllLines(n).straightness = tmpRatio;

                            % Angle between normal vectors of source node and target node
                            CurrentSourceNode = regionIndex(ClosestCutPointsSIndex(n));
                            CurrentTargetNode = regionIndex(ClosestCutPointsTIndex(n));
                            RegionA = CurrentPreimProps(ConcaveRegions==SelectedRegions(CurrentSourceNode,13),[1 2 3 4]);%load both regions: coordinates AND normal vectors!
                            RegionB = CurrentPreimProps(ConcaveRegions==SelectedRegions(CurrentTargetNode,13),[1 2 3 4]);%load both regions: coordinates AND normal vectors!
                            AllAngles = zeros(size(RegionA,1),size(RegionB,1),'double');%A=row, B=colums (opposite for distance calc!)
                            for l = 1:size(RegionA,1)%full loop over all combinations of cutting between region A and B!
                                for m = 1:size(RegionB,1)
                                        % optimizes for the smallest angle of two vectors to the connecting line!
                                        ConnectingVectorAB = RegionB(m,1:2)-RegionA(l,1:2);  % vector from pixel in region A to B
                                        ConnectingVectorAB = ConnectingVectorAB/norm(ConnectingVectorAB);
                                        ConnectingVectorBA = -ConnectingVectorAB;
                                        AngleDeviationA = acos(dot(RegionA(l,3:4),ConnectingVectorAB));  % Angle between the normal vector and the connectiong vector=deviation from ideal geometry
                                        AngleDeviationB = acos(dot(RegionB(m,3:4),ConnectingVectorBA));  % Angle between the normal vector and the connectiong vector=deviation from ideal geometry
                                        MeanAngleDeviation = (AngleDeviationA+AngleDeviationB)/2;  % ranges between 0 and 180 degree, 0 being the ideal geometry
                                        AllAngles(l,m) = pi-MeanAngleDeviation;  % this is done just to conform with the further angle scoring where 180 is considered best, 0 worst
                                end
                            end
                            AllAngles = real(AllAngles);
                            tmpAngle = max(AllAngles(:));  % max(acos)=pi, exactly what we are looking for (180 degree geometry)
                            % store measurements
                            AllLines(n).angle = tmpAngle;

                        end
                    end

%                     toc
                    % ---- Bottleneck -- end ----------------------------------------------------------------------------------------------------------------
                    % ---------------------------------------------------------------------------------------------------------------------------------------
                end
            else
                AllLines = struct();
            end


            if ~isempty(struct2cell(AllLines(:)))

                % Remove lines that didn't satisfy criteria - "is empty"
                celltmp = struct2cell(AllLines');
                indexEmpty = cellfun(@isempty,celltmp(1,:));
                AllLines = AllLines(~indexEmpty);

                %% Search for best cut
                if numel(AllLines) == 1
                    % We have no other choice but one possible cut.
                    BestLinesIndex = 1;
                else
                    % We have some cutting options. Look for optimal one.
                    %=============debug=============
                    if debug
                        % Display lines on top of object intensity image
                        AllLinesImage = zeros(size(padInt));
                        for d = 1:length(AllLines)
                            AllLinesImage(AllLines(d).lineimage>0) = 1;
                        end
                        [I, J] = find(logical(AllLinesImage));

                        figure(h), imagesc(padInt)
                        title(sprintf('Object # %d', i))
                        colormap(gray)
                        hold on
                        scatter(J, I, 150, 'y', 's', 'MarkerFaceColor', 'y')
                        scatter(SelectedNodeCoordList(:,2), SelectedNodeCoordList(:,1), 3000, 'r', '.')
                        hold off
                        pause(1)
                    end
                    %===========debug-end===========


                    %% Select best line and create cut mask

                    %%% Optimization function
                    optfunc = @(a,b,c,d,e,f,g,h) a - 2*b - c - d - e + 2*f - g - 2*h;

                    %%% Combine measurements
                    % for line
                    lineMaxInt = cat(1,AllLines.maxint);
                    lineMeanInt = cat(1,AllLines.meanint);
                    lineStraight = cat(1,AllLines.straightness);
                    lineAngle = cat(1,AllLines.angle);
                    lineLength = cat(1,AllLines.length);
                    lineQuantInt = cat(1,AllLines.quantint);

                    % for resulting objects
                    solobjs = cat(1,AllLines.solobj);
                    formobjs = cat(1,AllLines.formobj);
                    [~,smallindex] = min(cat(1,AllLines.areasobj),[],2);
                    solobj = zeros(length(solobjs),1);
                    formobj = zeros(length(formobjs),1);
                    for k = 1:size(solobjs,1)
                        solobj(k,1) = solobjs(k,smallindex(k));% solidity of the smaller object
                        formobj(k,1) = formobjs(k,smallindex(k));% "form factor" (transformed) of the smaller object
                    end

                    %%% Select best line
                    % scale variables
                    BestLines = optfunc(solobj, formobj, ...
                                        lineMeanInt.*100, lineMaxInt.*10, lineQuantInt.*10, ...
                                        lineAngle, lineStraight./10, lineLength./10);
                    % take highest scoring line
                    [~,BestLinesIndex] = sort(BestLines,'descend');
                end

                %=============debug=============
%                 for z=1:length(BestLinesIndex)
%                     BestLineOnIntImage = padInt;
%                     BestLineOnIntImage(AllLines(BestLinesIndex(z)).lineimage>0) = quantile(padInt(:),0.998);
%                     figure(h),imagesc(BestLineOnIntImage)
%                 end
                if debug
                    BestLineImage = zeros(size(padInt));
                    BestLineImage(AllLines(BestLinesIndex(1)).lineimage>0) = 1;
                    [I, J] = find(logical(BestLineImage));
                    figure(h),imagesc(padInt)
                    title(sprintf('Object # %d', i))
                    colormap(gray)
                    hold on
                    scatter(J, I, 150, 'y', 's', 'MarkerFaceColor','y')
                    hold off
                    pause(1)
                end
                %===========debug-end===========

                %%% Create cut mask
                if numel(BestLinesIndex) > numel(AllLines)
                    fprintf('Failed to find a more optimal cut for object # %d\n',i)
                else
                    % Choose the best line for cutting.
                    imBestLine = AllLines(BestLinesIndex(1)).lineimage;
                    % Do actual cutting.
                    if max(imBestLine(:))>0
                        %% Reverse padding and create final image
                        imBestLine = imBestLine((padSize(1)+1):(end-padSize(1)),(padSize(2)+1):(end-padSize(2)));

                        %%% Map back the linear indices and get indices for final image
                        [rMini, cMini ] = find(imBwMini);

                        % Get indices for final image (note that mini image might have
                        % permitted regions of other cells and thus boxes cannot be
                        % directly overlaid).
                        wMini = sub2ind(size(imBwMini),rMini,cMini);
                        r = rMini-1+N(i);
                        c = cMini-1+W(i);
                        w = sub2ind(size(CutMask),r,c);

                        CutMask(w) = imBestLine(wMini);
                        %figure,imagesc(CutMask)
                    end
                end
            end
        end
%           fprintf('Object # %d\n',i)
    end
end

CutMask = CutMask>0;
LineStrel = strel('disk',1,0);
CutMask = imdilate(CutMask,getnhood(LineStrel));

end


