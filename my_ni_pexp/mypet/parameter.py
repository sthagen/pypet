'''
Created on 17.05.2013

@author: Robert Meyer
'''

import logging
import petexceptions as pex
import tables as pt
import numpy as np
import scipy.sparse as spsp
import copy
from mypet.utils.helpful_functions import nest_dictionary
from mypet import globally




class BaseParameter(object):
    ''' Specifies the methods that need to be implemented for a Trajectory Parameter
    
    It is initialized with a location that specifies its position within the Trajectory, e.g.:
    Parameters.group.paramname
    The shorter name of the parameter is name=paramname, accordingly.
        
    For storing a parameter into hdf5 format the parameter implements a full node, how the storage 
    in the node is handled is left to the user.
        
    The parameter class can instantiate a single parameter as well as an array with several 
    parameters (of the same type) for exploration.
    
    Parameters can be locked to forbid further modification.
    If multiprocessing is desired the parameter must be pickable!
    ''' 
    def __init__(self, fullname):
        self._fullname = fullname
        split_name = fullname.split('.')
        self._name=split_name.pop()
        self._location='.'.join(split_name)
        self._comment = ''
        self._length = 0
        self._locked = False

    def __len__(self):
        return self._length

    def _rename(self, fullname):
        self._fullname = fullname
        split_name = fullname.split('.')
        self._name=split_name.pop()
        self._location='.'.join(split_name)

    def get_comment(self):
        return self._comment

    def is_array(self):
        return len(self)>1


    def is_locked(self):
        return self._locked

    def get_location(self):
        return self._location
     
    def __len__(self):
        ''' Returns the length of the parameter.
        
        Only parameters that will be explored have a length larger than 1.
        If no values have been added to the parameter it's length is 0.
        '''
        return self._length
    
    # def __getitem__(self,key):
    #     if not self.has_value(key):
    #         raise KeyError('%s has entry named %s.' %(self._fullname,key))
    #     if not isinstance(key, str):
    #         raise TypeError('None string keys are not supported!')
    #
    #     return getattr(self, key)
    
    def __store__(self):
        raise NotImplementedError( "Should have implemented this." )

    def __load__(self, load_dict):
        raise NotImplementedError( "Should have implemented this." )


    def to_str(self):
        ''' String representation of the value represented by the parameter. Note that representing
        the parameter as a string accesses it's value, but for simpler debugging, this does not
        lock the parameter!
        '''
        old_locked = self._locked
        try :
            return str(self.evaluate())
        except Exception, e:
            return 'No Evaluation possible (yet)!'
        finally:
            self._locked = old_locked


    def __str__(self):
        return '%s: %s' % (self._fullname, self.to_str())

    def unlock(self):
        ''' Unlocks the locked parameter.'''
        self._locked = False

    def lock(self):
        self._locked = True

    def evaluate(self):
        raise NotImplementedError( "Should have implemented this." )

    def gfn(self,valuename=None):
        ''' Short for get_fullname '''
        return self.get_fullname(valuename)
    
    def get_fullname(self,valuename=None):
        ''' param.get_fullname(valuname) -> Returns the fullname of the parameter 
        
        For example:
            param.gfn('myentry') could return Parameter.myparam.myentry
        
        Calling get_fullname() returns the full name of the parameter ignoring the entries.
        '''
        if not valuename:
            return self._fullname
        if not self.has_value(valuename):
            raise AttributeError('Parameter has not entry ' + valuename +'.')
        return self._fullname +'.'+ valuename
    
    def has_value(self,valuename):
        ''' Checks whether a parameter as a specific value entry.'''
        raise NotImplementedError( "Should have implemented this." )

    def __contains__(self, item):
        return self.has_value(self, item)

    def set(self, *args,**kwargs):
        ''' Sets specific values for a parameter.
        Has to raise ParameterLockedException if parameter is locked.

        For example:
        >>> param1.set(val1=5, val2=6.0)
        
        >>> print parm1.val1 
        >>> 5
        '''
        raise NotImplementedError( "Should have implemented this." )



    def get(self,name):
        raise NotImplementedError( "Should have implemented this." )
    
    def explore(self, expdict,**kwexpdict):
        ''' The default method to create and explored parameter containing an array of entries.

        **kwexpdict is a dictionary containing all entries as lists
        For example:
        >>> param.explore(**{'entry1':[1,2,3],'entry2'=[3.0,2.0,1.0]})

        You can also call it via
        >>> param.explore({'entry1':[1,2,3],'entry2'=[3.0,2.0,1.0]})

        '''
        raise NotImplementedError( "Should have implemented this." )
    
    def set_parameter_access(self, n=0):
        ''' Prepares the parameter for further usage, and tells it which point in the parameter space should be
        accessed for future calls.
        :param n: The index of the parameter space point
        :return:
        '''
        raise NotImplementedError( "Should have implemented this." )
        
    def get_class_name(self):  
        return self.__class__.__name__

    def get_name(self):
        ''' Returns the name of the parameter.'''
        return self._name

    def get_entry_names(self):
        ''' Returns a list of all entry names with which the parameter can be accessed
        '''
        raise NotImplementedError( "Should have implemented this." )

    def is_empty(self):
        return len(self) == 0

    def shrink(self):
        ''' If a parameter is explored, i.e. it is an array, the whole exploration is deleted,
        and the parameter is no longer an array.
        :return:
        '''
        raise NotImplementedError( "Should have implemented this." )

    def empty(self):
        '''Erases all data in the parameter. If the parameter was an explored array it is also shrunk.
        '''
        raise NotImplementedError( "Should have implemented this." )
      
class Parameter(BaseParameter):
    ''' The standard parameter that handles creation and access to simulation parameters.
    
    Supported Data types are int, string, bool, float and numpy arrays.
    The actual data entries are stored in the _data list, each element is a Data item.
    
    If the parameter is not an array the list has only a single data element.
    Each parameter can have several entries (which are stored in a Data item) as entryname value pairs 
    of supported data.
    
    Entries can be accessed and created via natural naming:
    >>> param.entry1 = 3.8
    
    >>> print param.entry1
    >>> 3.8
    
    Note that the user cannot modify entries of parameter arrays except for the very first parameter.
    In fact, changing an entry of a parameter array deletes the array and reduces _data list to contain
    only a single parameter.
    To change the whole parameter array, the corresponding methods in the trajectory should be called,
    like explore, for instance.
    '''
   
    # The comment that is added if no comment is specified
    standard_comment = 'Dude, please explain a bit what your fancy parameter is good for!'

    def __init__(self, fullname,*args,**kwargs):
        super(Parameter,self).__init__(fullname)
        self._comment= Parameter.standard_comment
        self._data={} #The Data
        self._explored_data={} #The Explored Data
        self._evaluate_string = None
        self._not_admissable_names = set(dir(self))

        
        self._logger = logging.getLogger('mypet.parameter.Parameter=' + self._fullname)
        
        self.set(*args,**kwargs)

        self._fullcopy = False


       
    def __getstate__(self):
        ''' Returns the actual state of the parameter for pickling. 
        '''
        result = self.__dict__.copy()
        result['_data'] = self._data.copy()

        # If we don't need a full copy of the Parameter (because a single process needs only access to a single point
        #  in the parameter space we can delete the rest
        if not self._fullcopy :
            result['_explored_data'] = {}

        del result['_logger'] #pickling does not work with loggers
        return result


    def __setstate__(self, statedict):
        ''' Sets the state for unpickling.
        '''
        self.__dict__.update( statedict)
        self._logger = logging.getLogger('mypet.parameter.Parameter=' + self._fullname)
      
        
    def set_parameter_access(self, n=0):
        if n >= len(self) and self.is_array():
            raise ValueError('You try to access the %dth parameter in the array of parameters, yet there are only %d potential parameters.' %(n,len(self)))
        else:
            for key, vallist in self._explored_data.items():
                self._data[key] = vallist[n]

    def has_value(self,valuename):
        return valuename in self._data

    def _is_supported_data(self, data):
        ''' Checks if input data is supported by the parameter'''
        #result = isinstance(data, ( np.int, np.str, np.float, np.bool, np.complex))

        if isinstance(data, np.ndarray):
            dtype = data.dtype
            if np.issubdtype(dtype,np.str):
                dtype = np.str
        else:
            dtype=type(data)


        return dtype in globally.PARAMETER_SUPPORTED_DATA


    def _values_of_same_type(self,val1, val2):
        ''' Checks if two values are of the same type.
        
        This is important for exploration and adding of elements to the parameter array.
        New added elements must agree with the type of previous elements.
        '''
        
        if not type(val1) == type(val2):
            return False
        
        if type(val1) == np.array:
            if not val1.dtype == val2.dtype:
                return False
            
            if not np.shape(val1)==np.shape(val2):
                return False
        
        return True
        

    def add_comment(self,comment):
        ''' Adds a comment to the current comment. The comment is separated from the previous comment by a semicolon and
        a line break.
        
        :param comment: The comment as string which is added to the existing comment
        '''
        #Replace the standard comment:
        if self._comment == Parameter.standard_comment:
            self._comment = comment
        else:
            self._comment = self._comment + ';\n ' + comment
            
            
       
    def __setattr__(self,name,value):
        
        if name[0]=='_':
            self.__dict__[name] = value
        else:
            self.set_single(name,value)
        
    def set(self,*args,**kwargs):

        if len(args)==1:
            if isinstance(args[0],list):
                args = args[0]
            elif isinstance(args[0],dict):
                kwargs = args[0]
                args=[]

        if len(args) == 2:
            if isinstance(args[0], list) and isinstance(args[1], dict):
                kwargs = args[1]
                args = args[0]


        for idx, arg in enumerate(args):
            valname = 'val' + str(idx)
            setattr(self, valname, arg)

        for key, arg in kwargs.items():
            setattr(self, key, arg)

    def _test_evaluation(self):
        old_locked = self._locked
        try:
            eval(self._evaluate_string)
        except Exception,e:
            self._logger.warning('Your evaluate expression >>%s<< failed to evaluate with error: %s' % (self._evaluate_string,str(e)))
        finally:
            self._locked = old_locked

    
    def set_single(self,name,val):
        ''' Adds a single entry to the parameter.
        
        This method is called for statements like:
        >>> param.entry = 4
        
        If the parameter was originally an array, the array is deleted because a setting is change 
        of the default entries of the parameter.
        '''


        if name in self._not_admissable_names:
            raise AttributeError('Your parameter %s cannot have %s as an entry, the name is similar to one of it\'s methods'
            % (self._fullname,name))

        if self.is_locked():
            raise pex.ParameterLockedException('Parameter ' + self._name + ' is locked!')


        # The comment is not in the _data list:
        if name == 'Comment' or name=='comment':
            self._comment = val
            return

        if name in ['EvalStr','evalstr','EvaluateString','evaluatestring']:
            assert isinstance(val,str)
            self._evaluate_string=val
            self._test_evaluation()
            return

        if name == 'FullCopy' or name =='fullcopy':
            self.set_copy_mode(val)
            return

        if name == 'val' or name == 'Val':
            raise AttributeError('Sorry, cannot add entry >>val<< or >>Val<<. These names are reserved for for fast access to the evaluation of the parameter.')


        if self.is_array():
            raise AttributeError('Your Parameter is an explored array can no longer change values!')


        val = self._convert_data(val)

        if not self._is_supported_data(val):
            raise AttributeError('Unsupported data type: ' +str(type(val)))

        self._data[name] = val

        if not self._evaluate_string:
            self._evaluate_string = 'self.'+name




    def _convert_data(self, val):
        ''' Converts data, i.e. sets numpy arrays immutable.

        :param val: the val to convert
        :return: the numpy type val
        '''
        if isinstance(val, np.ndarray):
            val.flags.writeable = False
            return val

        return val

    def get_entry_names(self):
        return self._data.keys()
        
    def get_array(self):
        if not self._isarray():
            raise TypeError('Your parameter is not array, so cannot return the explored values')
        else:
            return_dict={}
            for key, vallist in self._explored_data.items():
                return_dict[key] = vallist[:]
            return return_dict


    def to_dict(self):
        return self._data.copy()

    def explore(self, *args, **kwargs):
        ''' Changes a parameter to an array to allow exploration.
        
        *args and **kwargs are treated as in >>set(*arg,**kwargs)<< yet they need to contain
        lists of values of equal length that specify the exploration.
        '''
        if self.is_locked():
            raise pex.ParameterLockedException('Parameter %s is locked!' % self._fullname)

        if self.is_array():
            raise TypeError('Your Parameter %s is already explored, cannot explore it further!' % self._name)


        combined_args = self._data_sanity_checks(args, kwargs)

        self._length = self._length_check(combined_args)

        self._explored_data = combined_args
        self.lock()

    def _length_check(self,combined_args):
        actual_length = -1

        for key, vallist in combined_args.items():
            list_length = len(vallist)
            if actual_length == -1:
                actual_length = list_length
            elif actual_length != list_length:
                raise ValueError('The entries you want to explore are not of the same length!')
            else:
                pass # Everything's fine

        if actual_length == -1:
            raise ValueError('Something is wrong, your exploration of parameter >>%s<< did not contain a single entry to explore.' % self._name)
        elif actual_length == 1:
            raise ValueError('The length of your exploration is 1, why do you want to explore >>%s<< anyway, better change the values of the parameter instead directly.' % self._name)
        else:
            return actual_length



    def _data_sanity_checks(self, args, kwargs):

        combined_args = {}

        temp_dict = kwargs.copy()

        ## combine both args and kwargs, and add val'i' as the keyword:
        for idx, arglist in enumerate(args):

            entrystring = 'val'+str(idx)

            if entrystring in kwargs:
                raise ValueError('You have stuff to explore in args, as well as the corresponding keyword %s in kwargs.' % entrystring)

            temp_dict[entrystring]=arglist

        ## Now check and convert the data if necessary:
        for key, vallist in temp_dict.items():
            if not isinstance(vallist,list):
                raise TypeError('If you want to explore a parameter you need to supply lists of values %s, is not a list but %s.' %(key,str(type(vallist))))
            combined_args[key] =[]

            if not key in self._data:
                raise AttributeError('%s is not in your default entries of your parameter. You can only explore data that is part of your parameter.'%key)

            default_val = self._data[key]

            for val in vallist:
                newval = self._convert_data(val)

                if not self._is_supported_data(newval):
                    raise TypeError('%s contains items of not supported type %s.' % (key,str(type(newval))))

                if not self._values_of_same_type(newval,default_val):
                    raise TypeError('%s is not of the same type as the original entry value, new type is %s vs old type %s.' % (key, str(type(newval)),str(type(default_val))))


                combined_args[key].append(newval)

        return combined_args


    def _store_data(self, store_dict):

        store_dict['Data'] = {}
        for key, val in self._data.items():
            store_dict['Data'][key] = [self._data[key]]

        if self.is_array():
            store_dict['ExploredData'] = {}
            for key, val in self._explored_data.items():
                store_dict['ExploredData'][key] = self._explored_data[key][:]



    def _store_meta_data(self,store_dict):

        store_dict['Info'] = {'Name':[self._name],
                   'Location':[self._location],
                   'Comment':[self._comment],
                   'Type':[str(type(self))],
                   'Class_Name': [self.__class__.__name__],
                   'Length' : [self._length]}



    def _store_eval_expression(self,store_dict):

        if self._evaluate_string:
            store_dict['Info']['EvalStr'] = [self._evaluate_string]


    def __store__(self):
        store_dict={}
        self._store_meta_data(store_dict)
        self._store_data(store_dict)
        self._store_eval_expression(store_dict)

        return store_dict


    def _load_meta_data(self, load_dict):
        info_dict = load_dict['Info']

        self._name = info_dict['Name'][0]
        self._location = info_dict['Location'][0]
        self._comment = info_dict['Comment'][0]
        self._fullname = self._location +'.' + self._name
        self._length = info_dict['Length'][0]

        assert str(type(self)) == info_dict['Type'][0]
        assert self.__class__.__name__ == info_dict['Class_Name'][0]



    def _load_data(self, load_dict):

        for key, vallist in load_dict['Data'].items():
            self._data[key] = vallist[0]


        if 'ExploredData' in load_dict:
            self._explored_data = load_dict['ExploredData']


    def _load_eval_expression(self,load_dict):

        if 'EvalStr' in load_dict['Info']:
            self._evaluate_string=load_dict['Info']['EvalStr'][0]
            self._test_evaluation()
        else:
            self._evaluate_string=None




    def __load__(self,load_dict):
        self._load_meta_data(load_dict)
        self._load_data(load_dict)
        self._load_eval_expression(load_dict)



    def set_copy_mode(self, val):
        assert isinstance(val, bool)
        self._fullcopy = val


    def get(self, name):

        if name == 'FullCopy' or name =='fullcopy':
            return self._fullcopy

        if name in ['EvalStr','evalstr','EvaluateString','evaluatestring']:
            return self._evaluate_string

        if name == 'val' or name == 'Val':
            return self.evaluate()

        if name == 'comment' or name=='Comment':
            return self._comment
            
        if not name in self._data:
            raise AttributeError('Parameter %s does not have attribute or entry %s.' %(self._fullname,name))
        

        self.lock() # As soon as someone accesses an entry the parameter gets locked
        return self._data[name]

    def evaluate(self):
        if self._evaluate_string:
            return eval(self._evaluate_string)
        else:
            return None

    
    def __getattr__(self,name):
        if (not '_data' in self.__dict__ or
            not '_fullname' in self.__dict__):

            raise AttributeError('This is to avoid pickling issues!')
        
        return self.get(name)

    def __delattr__(self, item):
        if  item[0] == '_':
            del self.__dict__[item]
        elif self.is_locked():
            raise pex.ParameterLockedException('Parameter %s is locked!' % self._fullname)
        elif self.is_array():
            raise TypeError('Your parameter %s is an explored array, cannot delete items, call >>shrink()<< before you delete entries.' % self.get_name())
        elif self.has_value(item):
            del self._data[item]
        else:
            raise AttributeError('%s is not an entry of you parameter %s, cannot delete it.' % (item,self.get_name()))
 
    def shrink(self):
        ''' Shrinks the parameter array to a single parameter.
        '''
        if self.is_locked():
            raise pex.ParameterLockedException('Parameter %s is locked!' % self._fullname)

        self._explored_data={}
        self._length = 1

    def empty(self):
        ''' Erases all data in the Parameter, if the parameter was explored, it is shrunk as well.
        '''
        if self.is_locked():
            raise pex.ParameterLockedException('Parameter %s is locked!' % self._fullname)

        self.shrink()
        self._data={}
        self._length = 0
    
     


class SparseParameter(Parameter):
    ''' A parameter class that supports sparse scipy matrices.
    
    Supported formats are csc,csr and lil. Note that all sparce matrices are converted to
    csr before storage.
    In case of a parameter array the matrices need to be of the very same size, i.e. the amount
    of nonzero entries must be the same.
    '''
    separator = '_spsp_'

    def _is_supported_data(self, data):
        ''' Simply checks if data is supported '''
        if super(SparseParameter,self)._is_supported_data(data):
            return True
        if spsp.isspmatrix_lil(data) or spsp.isspmatrix_csc(data) or spsp.isspmatrix_csr(data):
            return True
        return False

    def _values_of_same_type(self,val1, val2):
        if not super(SparseParameter,self)._values_of_same_type(val1, val2):
            return False
        
        if spsp.issparse(val1):
            if not val1.dtype == val2.dtype:
                return False
            if not len(val1.nonzero()[0]) == len(val2.nonzero()[0]):
                return False

        return True

    def set_single(self,name,val):
        if SparseParameter.separator in name:
            raise AttributeError('Sorry your entry cannot contain >>%s<< this is reserved for storing sparse matrices.' % SparseParameter.separator)

        super(SparseParameter,self).set_single(name,val)

    def _load_data(self, load_dict):
        data_dict = load_dict['Data']

        self._load_sparse_data(data_dict)

        if 'ExploredData' in load_dict:
            explored_dict = load_dict['ExploredData']
            self._load_sparse_data(explored_dict)

        super(SparseParameter,self)._load_data(load_dict)

    def _load_sparse_data(self, data_dict):


        sparse_matrices = {}
        for key,val in data_dict.items():
            if SparseParameter.separator in key:
                sparse_matrices[key]=val
                del data_dict[key]


        sparse_matrices = nest_dictionary(sparse_matrices, SparseParameter.separator)

        for name, mat_dict in sparse_matrices.items():
            arformat = mat_dict['format']
            ardata = mat_dict['data']
            arindptr= mat_dict['indptr']
            arindices = mat_dict['indices']
            arshape = mat_dict['shape']
            arstoredformat=mat_dict['storedformat']

            sparsematlist = []
            for idx in range(len(arformat)):
                matformat = arformat[idx]
                storedformat=arstoredformat[idx]
                data = ardata[idx]
                indptr = arindptr[idx]
                indices = arindices[idx]
                shape = arshape[idx]

                if storedformat == 'csr':
                    sparsemat = spsp.csr_matrix((data, indices, indptr),shape)
                    if matformat == 'lil':
                        sparsemat = sparsemat.tolil() #Ui Ui might be expensive
                    if matformat == 'csc':
                        sparsemat = sparsemat.tocsc()
                else:
                    self._logger.error('If the matrix was not stored in csr format, I am afraid I have to tell you that other formats are not supported yet.')


                sparsematlist.append(sparsemat)

            data_dict[name] = sparsematlist


    def _store_data(self, store_dict):
        super(SparseParameter,self)._store_data(store_dict)

        data_dict = store_dict['Data']

        self._store_sparse_data(data_dict)

        if 'ExploredData' in store_dict:
            explored_dict = store_dict['ExploredData']
            self._store_sparse_data(explored_dict)


    def _store_sparse_data(self,data_dict):



        for key, val_list in data_dict.items():
            if spsp.isspmatrix(val_list[0]):
                del data_dict[key]
                data_dict[key+SparseParameter.separator+'format']=[]
                data_dict[key+SparseParameter.separator+'data']=[]
                data_dict[key+SparseParameter.separator+'indptr'] = []
                data_dict[key+SparseParameter.separator+'indices'] = []
                data_dict[key+SparseParameter.separator+'shape']=[]
                data_dict[key+SparseParameter.separator+'storedformat'] = []
                for idx, val in enumerate(val_list):
                    data_dict[key+SparseParameter.separator+'format'].append(val.format)
                    val = val.tocsr()
                    data_dict[key+SparseParameter.separator+'data'].append(val.data)
                    data_dict[key+SparseParameter.separator+'indptr'].append(val.indptr)
                    data_dict[key+SparseParameter.separator+'indices'].append(val.indices)
                    data_dict[key+SparseParameter.separator+'shape'].append(np.array(np.shape(val)))
                    data_dict[key+SparseParameter.separator+'storedformat'].append(val.format)





      

            
                            

class BaseResult(object):
    ''' The basic result class.
    
    It is a subnode of the tree, but how storage is handled is completely determined by the user.
    
    The result does know the name of the parent trajectory and the file because it might
    autonomously write results to the hdf5 file.
    '''
            
    def __init__(self, fullname):
        self._fullname = fullname
        split_name = fullname.split('.')
        self._name=split_name.pop()
        self._location='.'.join(split_name)

    def _rename(self, fullname):
        self._fullname = fullname
        split_name = fullname.split('.')
        self._name=split_name.pop()
        self._location='.'.join(split_name)

    def get_name(self):
        return self._name
    
    def get_fullname(self):
        return self._fullname

    def get_location(self):
        return self._location
    
    def gfn(self):
        return self.get_fullname()
    
    def get_class_name(self):  
        return self.__class__.__name__

    def __store__(self):
        raise NotImplementedError('Implement this!')

    def __load__(self, load_dict):
        raise  NotImplementedError('Implement this!')


    def is_empty(self):
        ''' Returns true if no data is stored into the result
        :return:
        '''
        raise NotImplementedError('You should implement this!')

    def empty(self):
        ''' Erases all data in the result and afterwards >>is_empty()<< should evaluate true
        :return:
        '''
        raise NotImplementedError('You should implement this!')

class SimpleResult(BaseResult):
    ''' Light Container that stores tables and arrays. Note that no sanity checks on individual data is made
    and you have to take care, that your data is understood by the Storage Service! It is assumed that
    results tend to be large and therefore sanity checks would be too expensive!
    '''

    def __init__(self, fullname, *args, **kwargs):
        super(SimpleResult,self).__init__(fullname)
        self._data = {}
        self._comment = None

        self.set(*args,**kwargs)



    def is_empty(self):
        return len(self._data)== 0

    def empty(self):
        self._data={}


    def set(self,*args, **kwargs):

        for idx,arg in enumerate(args):
            valstr = 'res'+str(idx)
            self.set_single(valstr,arg)

        for key, arg in kwargs.items():
            self.set_single(key,arg)

    def set_single(self, name, item):

        if name in ['comment', 'Comment']:
            assert isinstance(item,str)
            self._comment = item

        if name == 'Info':
            raise ValueError('>>Info<< is reserved for storing  information like name and location of the result etc.')

        if isinstance(item, (np.ndarray,dict)):
            self._data[name] = item
        else:
            raise TypeError('Your result >>%s<< of type >>%s<< is not supported.' % (name,str(type(item))))



    def __store__(self):
        store_dict ={}
        self._store_meta_data(store_dict)
        store_dict.update(self._data)
        return store_dict


    def _store_meta_data(self,store_dict):

        store_dict['Info'] = {'Name':[self._name],
                   'Location':[self._location],
                   'Type':[str(type(self))],
                   'Class_Name': [self.__class__.__name__]}

        if self._comment:
            store_dict ['Info']['Comment'] = [self._comment]


    def __load__(self, load_dict):
        info_dict = load_dict.pop('Info')
        self._load_meta_data(info_dict)

        self._data = load_dict


    def _load_meta_data(self, info_dict):

        self._name = info_dict['Name'][0]
        self._location = info_dict['Location'][0]
        self._fullname = self._location +'.' + self._name


        assert str(type(self)) == info_dict['Type'][0]
        assert self.__class__.__name__ == info_dict['Class_Name'][0]

        if 'Comment' in info_dict:
            self._comment = info_dict['Comment'][0]
        else:
            self._comment = None

    def __delattr__(self, item):
        if item[0]=='_':
            del self.__dict__[item]
        elif item in self._data:
            del self._data[item]
        else:
            raise AttributeError('Your result >>%s<< does not contain %s.' % (self.get_name(),item))

    def __setattr__(self, key, value):
        if key[0]=='_':
            self.__dict__[key] = value
        else:
            self.set_single(key, value)

    def __getattr__(self, name):

        if (not '_data' in self.__dict__ or
            not '_fullname' in self.__dict__):

            raise AttributeError('This is to avoid pickling issues!')

        if name in ['Comment', 'comment']:
            return self._comment

        if not name in self._data:
            raise  AttributeError('>>%s<< is not part of your result >>%s<<.' % (name,self._fullname))

        return self._data[name]

