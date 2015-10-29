function strPrintName = gcf2pdf(strRootPath,strFigureName,varargin)
% help for gcf2pdf 
%
% gcf2pdf converts current figure into a vectorized pdf file.
%
% usage: 
% strPrintName = gcf2pdf(strRootPath,strFigureName,varargin)
%
% remarks/changes
% BS, 080827: added varargin to pass 'overwrite' parameter, to overwrite
%   existing output files
% BS, 080913: added varargin to pass 'zbuffer' parameter, to force the
%   renderer to use zbuffer. Renderer painter is default for gcf2pdf, to
%   maximize vector graphics for pdf output.
% BS, 081030: added varargin 'noheader' option
% BS, 120326: added varargin 'noresize' option
% BS, 090514: added optional paper size input. if varargin contains any of
%   the following strings 'A0','A1','A2','A3','A4','A5', that paper size will
%   be used instead of the default A4.

    % activate current figure
    figure(gcf)
    drawnow

    strPrintName = '';
    
    if nargin == 0
        if ispc
            
            strRootPaths = {pwd,'C:\Documents and Settings\imsb\Desktop\', 'C:\Users\pauli\Desktop\', 'C:\Users\pelkmans\Desktop\'};
            strRootPath = strRootPaths{find(cellfun(@isdir,strRootPaths),1,'first')};

        else
            strRootPath = '/Volumes/share-2-$/Data/Users/Herbert/';
        end
        strFigureName = 'CurrentFigure2PDF_';
    elseif nargin == 1
        strFigureName = 'CurrentFigure2PDF';
    end
    
    try
        fileattrib(strRootPath);
    catch
        error('%s is not a valid path',strRootPath)
    end

    %%% allow gcf2pdf to also see hidden windows
    strOrigSetting = get(0,'ShowHiddenHandles');
    if strcmp(strOrigSetting,'off')
        set(0,'ShowHiddenHandles','on');
    end    
    
    set(0,'ShowHiddenHandles','on')
    set(gcf,'RendererMode','manual')    
    if ~isempty(find(strcmpi(varargin,'zbuffer'), 1))    
        disp(sprintf('%s: using renderer: Z-Buffer',mfilename))
        set(gcf,'Renderer','zbuffer')
    else
        disp(sprintf('%s: using renderer: Painters',mfilename))        
        set(gcf,'Renderer','painters')        
    end


    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    %%% NEW FEATURE: PRINT STACK TRACE AT TOP OF PLOT, TO RECORD
    %%% SCRIPTNAMES
    %%% BS, 080818, TRY ADDING THE FIGURE WINDOW NAME TO THE PLOT, IF
    %%% INTERESTING, AND/OR THE AXIS TITLE, IF PRESENT
    %%% ONLY IF THE NOHEADER OPTION IS NOT PASSED
    
    if isempty(find(strcmpi(varargin,'noheader')))        
        % init gcf information container
        strMFileName = '';

        % add window name if it doesnt contain 'Figure'
        strWindowName = get(gcf,'Name');
        if isempty(strfind(strWindowName,'Figure'))
            strMFileName = strWindowName;
        end
    
        % add figure axis title
        gcatitlehandle = get(gca,'Title');
        strAxisTitle = char(get(gcatitlehandle,'String'));
        if ~isempty(strAxisTitle) && isempty(strMFileName)
            strMFileName = strAxisTitle;
        elseif ~isempty(strAxisTitle) && ~isempty(strMFileName)
            strMFileName = [{strMFileName}; {strAxisTitle}];
        end
    
        try
            [si,i]=dbstack('-completenames');
            strMFileName = [{strMFileName};getlastdir(cellstr({si.file})')];
            strMFileName = strrep(strMFileName,'_','\_');
            if size(strMFileName,1)>1; strMFileName=flipud(strMFileName); end
        %     if ~isempty(strcmpi(strMFileName,'temp.m'))
            hold on
            axes('Layer','top','Color','none','Position',[0,0.01,.98,.98])
            text(0,1,[datestr(now,'[yymmdd HH:MM:SS] '),sprintf('[%s] ',strMFileName{:})],'FontSize',7,'Color',[.3 .3 .3],'Interpreter','none')
            axis off
            hold off
            drawnow

            % get ready to add scriptname to pdf file-name
            strMFileName = strtrim(strMFileName);
            strMFileName = strrep(strMFileName,'.m','');
            strMFileName = strrep(strMFileName,'\','');
            strMFileName = strrep(strMFileName,' ','_');

        %     end
        catch
            disp(' (UNABLE TO ADD STACK TRACE TO PLOT)')
        end
    end
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

    % prepare for pdf printing
    if ~any(strcmpi(varargin,'noresize'))
        scrsz = [1,1,1920,1200];
        set(gcf, 'Position', [1 scrsz(4) scrsz(3) scrsz(4)]);     
    end
    shading interp
    set(gcf,'PaperPositionMode','auto', 'PaperOrientation','landscape')
    set(gcf, 'PaperUnits', 'normalized'); 
    printposition = [0 .2 1 .8];
    
%     set(gcf, 'PaperUnits', 'inches');
%     printposition = [6.49 11.84 8.00 6.00]
    set(gcf,'PaperPosition', printposition)
    
    % check varargin for papersize references
    cellstrPaperSizes = {'A0','A1','A2','A3','A4','A5'};
    if sum(ismember(upper(varargin),cellstrPaperSizes))>0
        % IF NOHEADER CONTAINS PAPER SIZE REFERENCE, USE THIS
        strPaperSize = varargin(ismember(upper(varargin),cellstrPaperSizes));
        strPaperSize = strPaperSize{1};
        set(gcf, 'PaperType', strPaperSize);

%         set(gcf, 'PaperUnits', 'centimeters'); 
%         set(gcf, 'PaperSize', [51 22]);
    else
        % DEFAULT TO A4 PAPER SIZE
        set(gcf, 'PaperType', 'A4');   
    end           
    
    orient landscape

    drawnow
    
    if isempty(find(strcmpi(varargin,'overwrite')))
        filecounter = 1;
        if nargin == 0
    %         if isempty(strMFileName)
    %             strPrintName = fullfile(strRootPath,['gcf2pdf_',getlastdir(strRootPath),'_',num2str(filecounter),'.pdf']);
    %         else
                strPrintName = fullfile(strRootPath,[datestr(now,'yymmdd'),'_',sprintf('%s_',strMFileName{:}),getlastdir(strRootPath),'_',num2str(filecounter),'.pdf']);
    %         end
        elseif nargin == 1
            strPrintName = fullfile(strRootPath,[datestr(now,'yymmdd'),'_',strFigureName,'_',getlastdir(strRootPath),'_',num2str(filecounter),'.pdf']);                
        elseif nargin == 2
            strPrintName = fullfile(strRootPath,[datestr(now,'yymmdd'),'_',strFigureName,'_',num2str(filecounter),'.pdf']);
        else
            strPrintName = fullfile(strRootPath,[datestr(now,'yymmdd'),'_',strFigureName,'_',num2str(filecounter),'.pdf']);            
        end

        % replace not allowed characters...
        strPrintName(ismember(strPrintName,'!@#%^&*()[]{};<>,%=|')) = '_';    
        % remove pesky ':' after first 3 characters...
        strPrintName([false,false,false,ismember(strPrintName(4:end),':')]) = '_';
        
        % look for file, if present, increase increment
        filepresentbool = fileattrib(strPrintName);
        while filepresentbool
            filecounter = filecounter + 1;
            strPrintName = strrep(strPrintName,['_',num2str(filecounter-1),'.pdf'],['_',num2str(filecounter),'.pdf']);
            filepresentbool = fileattrib(strPrintName);
        end
    else
        % in case overwrite is set as an option
        strPrintName = fullfile(strRootPath,strFigureName);
        % replace not allowed characters...
        strPrintName(ismember(strPrintName,'!@#%^&*()[]{};<>,%=|')) = '_';
        % remove pesky ':' after first 3 characters...
        strPrintName([false,false,false,ismember(strPrintName(4:end),':')]) = '_';
        
        % look for file, if present, delete
        if fileattrib(strPrintName);        
            delete(strPrintName)
        end
    end    
    
    
    disp(sprintf('%s: stored %s',mfilename,strPrintName))
    print(gcf,'-dpdf',strPrintName);
%     close(gcf)

    if strcmp(strOrigSetting,'off')
        set(0,'ShowHiddenHandles','off');
    end    
    
    
    if ispc && nargin==0
        fprintf('%s: experimental, running gcf2pdf on windows with no input arguments. Therefore using ''go'' to open %s\n',mfilename,strPrintName)
        go(strPrintName)
    end
    
end


function boolIsDir=isdir(x)
    boolIsDir=fileattrib(char(x));
end