function matLocalizationMeasurements = CPgetSpotLocalizations(tempParentLocation,tempChildrenLocation,tempThirdLoc,CurrCellMembraneLocalization,tempTotalChildren,matEdge_NonEdge,matPerVector,matRadiousVector,i)
% Support Function which calculates multiple spatial features of spots;
%
%   ----------------------------------
%   Authors:
%   Nico Battich
%   Thomas Stoeger
%   Lucas Pelkmans
%   
%   Battich et al. 2013
%   Website: http://www.imls.uzh.ch/research/pelkmans.html

% global settings

pxDistOfInterest = 1.4142; % size of one pixel distance here square root of 1+1

tempMemLocationX = CurrCellMembraneLocalization(:,2);
tempMemLocationY = CurrCellMembraneLocalization(:,1);

%%%% initialize output
numPerVector = length(matPerVector);
numRadious = length(matRadiousVector);
matDisPerX1 = NaN(tempTotalChildren,numPerVector);
matDisRadY1 = NaN(tempTotalChildren,numRadious);
matMeanDis = NaN(tempTotalChildren,1);
matStdDis = NaN(tempTotalChildren,1);
matVarDis = NaN(tempTotalChildren,1);


%%%% FEATURES, which depend upon other spots %%%%%%%

if tempTotalChildren>1
    
    %%% get distances to other children
    tempChildrenDistance = squareform(pdist(tempChildrenLocation));
    
    %%% sort other spots based on proximity; sorting will allow a fast
    %%% calcuatation of the features.
    matSort = zeros(size(tempChildrenDistance));
    for j=1:tempTotalChildren
        matSort(j,:) = sort(tempChildrenDistance(j,:));
    end
    matSort = matSort(:,2:end); % Remove self spot.
    
    %%% calculate the radii required to include xpercentage of spots
    for j = 1:numPerVector
        IX = ceil((tempTotalChildren-1).* matPerVector(j));
        matDisPerX1(:,j) = matSort(:,IX);
    end
    
    %%% calculate the fraction of neighbours at given radii
    for j = 1:numRadious
        matDisRadY1(:,j) = sum(matSort< matRadiousVector(j),2)./(tempTotalChildren-1);
    end
    
    %%% calculate mean distances to other children
    nantempChildrenDistance = tempChildrenDistance;
    nantempChildrenDistance(nantempChildrenDistance==0) = nan;
    matMeanDis = nanmean(nantempChildrenDistance,2);
    matVarDis = nanvar(nantempChildrenDistance,[],2);
    matStdDis = sqrt(matVarDis); %Matlab would call sqrt(nanvar) in nansqrt. Thus save some computing time
end

clear nantempChildrenDistance; clear tempChildrenDistance;

%%%% FEATURES, which only depend parent and siblings of parent %%%%%%

%%% calculate distance to parent centroid
matDisToParentCentroid =...
    ((tempParentLocation(1)-tempChildrenLocation(:,1)).^2+...
    (tempParentLocation(2)-tempChildrenLocation(:,2)).^2).^(1/2);

%%% caculate distance to closest outline (matDistancesToOutline)
[matDistancesToOutline matMinIX] = smallestEuc(CurrCellMembraneLocalization(:,[2 1]),tempChildrenLocation(:,:)); % note that CurrCellMembraneLocalization has Y in first and X in second row

%%% obtain, whether closest membrane is adjacent to another cell
tempLabelIX = sub2ind(size(matEdge_NonEdge),tempMemLocationY(matMinIX), ...
    tempMemLocationX(matMinIX));
matOutlineLabel = ...
    matEdge_NonEdge(tempLabelIX);

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%% FEATURES, which only depend upon third object (nucleus) %%%%%%
%%%% as this calculation is quite time consuming, several trival %%
%%%% cases are checked at first to reduce computation time %%%%%%%%
%%%% if these features were deactivated, the total time of the %%%%
%%%% calculation of the spot features will be reduced to <50%  %%%%


suppIX = 1:tempTotalChildren; % Index of Child positions. Initiallizing this enumeration will speed up sequential filtering

bestIX = zeros(tempTotalChildren,1); % DebugOutput Index; while this will not be returned, it is very useful for debugging. consider commenting out all bestIX to save a few permille of processing time

matDisToThirdCentroid = zeros(tempTotalChildren,1);
matDisToOutlineThirdLine = zeros(tempTotalChildren,1);

f = matDistancesToOutline < 1.41421356; % if spot is within one pixel (sqrt(1+1)) distance to membrane, also use that membrane as third object distance
if any(f)
    %     bestIX(f) = matMinIX(f);
    curIX = matMinIX(f);
    ins = [tempMemLocationX(curIX) - tempThirdLoc(1),tempMemLocationY(curIX) - tempThirdLoc(2)];
    matDisToThirdCentroid(f) = (sum(ins.^2,2)).^(1/2);
    matDisToOutlineThirdLine(f) = matDistancesToOutline(f);
    bestIX(f) =  matMinIX(f);
end

if any(~f)
    %%% get membrane vector with smallest angle %%%%
    suppIX = suppIX(~f);
    
    % get vector starting from third object for all membrane locations.
    dMemLoc = [tempMemLocationX - tempThirdLoc(1),tempMemLocationY - tempThirdLoc(2)];
    % normalize the vectors to have a length of 1
    dMemDiv = (dMemLoc(:,1).^2 + dMemLoc(:,2).^2).^(1/2);
    dMemNorm = [dMemLoc(:,1)./dMemDiv dMemLoc(:,2)./dMemDiv];
    
    suppIXMembr = 1:size(dMemNorm,1);
    
    %%% now loop through individual spots %%%
    % note that while some speed improvements could be done without
    % looping, this would cost readability and memory
    for k=1:sum(~f)
        
        CurrAbsSpotID = suppIX(k);
        
        dSpotLoc = [tempChildrenLocation(CurrAbsSpotID,1) - tempThirdLoc(1),tempChildrenLocation(CurrAbsSpotID,2) - tempThirdLoc(2)];
        dSpotDiv = (dSpotLoc(:,1).^2 + dSpotLoc(:,2).^2).^(1/2);
        dSpotNorm = [dSpotLoc(:,1)./dSpotDiv dSpotLoc(:,2)./dSpotDiv];
        
        [distMemResSpots, bIX] = suppEucSquare(dMemNorm,dSpotNorm); %custom function, which outperforms matlab's function for this specialized case
        
        isTrivial = (bIX == matMinIX(CurrAbsSpotID)) | ...     % check if closest membrane also is the one with best angle
            (dMemDiv(bIX) <= dSpotDiv );                       % or if the membrane with the closest angle is closer to the third object than the spot
        
        if isTrivial
            ins = ((dMemLoc(bIX,1)-dSpotLoc(1)).^2+(dMemLoc(bIX,2)-dSpotLoc(2)).^2).^(1/2);
            matDisToThirdCentroid(CurrAbsSpotID) = dSpotDiv;
            matDisToOutlineThirdLine(CurrAbsSpotID) = ins;
            bestIX(CurrAbsSpotID) =  bIX;
            
        else %otherwise look for membranes with similar angle, which are closest.
            % obtain other membrane pixels with similar angle by using the
            % previously normalized vectors (all length 1) and geometrical
            % properties of isosceles triangles. This will be quite fast.
            fAngle = distMemResSpots < 0.12061729; % (2*sin(10*pi/180)= 0.3473).^2; % within +/- 10degrees.
            
            dMemDivToConsiderForProximity = dMemDiv(fAngle);
            suppIXMembrConsiderForProximity = suppIXMembr(fAngle);
            
            fProximity = dMemDivToConsiderForProximity <= dMemDiv(bIX); % logical
            suppIXMembrConsiderForSmallDeviation = suppIXMembrConsiderForProximity(fProximity); % integer index
            CurrdMemDiv = dMemDivToConsiderForProximity(fProximity);
            CurrdMemLoc = dMemLoc(suppIXMembrConsiderForSmallDeviation,:);
            
            % get membrane spots, where either x or y is within one
            % pixel distance
            if dSpotLoc(1) ~= 0   % rescale Y, if any X
                suit = abs((CurrdMemLoc(:,1)./dSpotLoc(1)).*dSpotLoc(2) - CurrdMemLoc(:,2))< pxDistOfInterest;
            elseif dSpotLoc(2) ~= 0 % rescale X, if any Y
                suit = abs((CurrdMemLoc(:,2)./dSpotLoc(2)).*dSpotLoc(1) - CurrdMemLoc(:,1))< pxDistOfInterest;
            else % membrane is at place of tertiary object; also spot has to be there. see previous filtering
                suit = CurrdMemLoc(:,1) == dSpotLoc(1) & CurrdMemLoc(:,2) == dSpotLoc(2);
            end
            
            suppIXMembrConsiderForSmallSuit = suppIXMembrConsiderForSmallDeviation(suit);
            
            if any(suit)
                [~, fff] = min(CurrdMemDiv(suit));
                
                nIX = suppIXMembrConsiderForSmallSuit(fff);
                ins = ((dMemLoc(nIX,1)-dSpotLoc(1)).^2+(dMemLoc(nIX,2)-dSpotLoc(2)).^2).^(1/2);
                matDisToOutlineThirdLine(CurrAbsSpotID) = ins;
                bestIX(CurrAbsSpotID) =  nIX;
                
            else
                ins = ((dMemLoc(bIX,1)-dSpotLoc(1)).^2+(dMemLoc(bIX,2)-dSpotLoc(2)).^2).^(1/2);
                matDisToOutlineThirdLine(CurrAbsSpotID) = ins;
                bestIX(CurrAbsSpotID) =  bIX;
                
            end
        end
        matDisToThirdCentroid(CurrAbsSpotID) = dSpotDiv;
    end
end

% Return Measurments
matLocalizationMeasurements = [matDistancesToOutline ...
    matOutlineLabel ...
    matDisToParentCentroid ...
    matDisToThirdCentroid ...
    matDisToOutlineThirdLine ...
    matMeanDis ...
    matStdDis ...
    matVarDis ...
    matDisPerX1 ...
    matDisRadY1];


% Commented out code for debugging: hopefully not needed anymore. note that
% it might has to be readjusted since variables defined slightly
% differently. will plot position of individual pixels and their
% propertiers.
% figure;
% hold on;
% scatter(tempMemLocationX(:,1),tempMemLocationY(:,1));
% scatter(tempChildrenLocation(:,1),tempChildrenLocation(:,2),'or','filled');
% scatter(tempThirdLoc(1),tempThirdLoc(2),'og','filled')
% scatter(tempMemLocationX(bestIX,1),tempMemLocationY(bestIX,1),'ok','filled');
%
% title(num2str(i))
% hold off;



end


function [DIS IX] = smallestEuc(A,B)
% support function, which gets the smallest euclidean distance for any B to
% any element of A. note that it only requires around 50% of the time when
% compared to the solution with the inbuild pdist2(X,Y,'euclidean','Smallest',1)
numStart = size(B,1);

DIS = NaN(numStart,1);
IX = NaN(numStart,1);


for j=1:numStart
    CurrX = A(:,1) - B(j,1);
    CurrY = A(:,2) - B(j,2);
    dist = CurrX.^2 + CurrY.^2;
    [cD IX(j)] = min(dist);
    
    DIS(j) = cD.^(1/2);
end
end



function [DIS IX] = suppEucSquare(A,B)

% support function, which gets the smallest euclidean distance for for vector B to
% any element of A. note that it allows to save some memory if there were a
% lot of spots present. Also note that DIS is the square of the euclidean
% distance

if size(B,1)~=1;
    error('second input for suppEucSquare must be vector')
else
    CurrX = A(:,1) - B(1);
    CurrY = A(:,2) - B(2);
    DIS = CurrX.^2 + CurrY.^2;
    [~, IX] = min(DIS);
end
end

