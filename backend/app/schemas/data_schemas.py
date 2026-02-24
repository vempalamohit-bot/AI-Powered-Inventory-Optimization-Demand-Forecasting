"""
Data Schema Mapping and Validation Layer
=========================================
This module provides unified schema definitions, field mapping, and validation  
for both CSV and JSON data sources to ensure consistent AI/ML processing.

Key Features:
- Maps JSON keys to database columns
- Validates required fields for forecasting/AI
- Handles field name variations (aliases)
- Provides type conversion and cleaning
- Supports both CSV and JSON inputs
"""

from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
import pandas as pd
from pydantic import BaseModel, Field, validator
from enum import Enum


class StockStatus(str, Enum):
    """Stock level categories"""
    OUT_OF_STOCK = "OUT_OF_STOCK"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    OPTIMAL = "OPTIMAL"


class TransactionType(str, Enum):
    """Sales transaction types"""
    NORMAL = "Normal"
    CLEARANCE = "Clearance"
    PROMOTIONAL = "Promotional"
    MARKDOWN = "Markdown"


class SalesChannel(str, Enum):
    """Sales channels"""
    ONLINE = "Online"
    STORE = "Store"
    WHOLESALE = "Wholesale"
    B2B = "B2B"


# ============================================================================
# PRODUCT SCHEMA DEFINITION
# ============================================================================

class ProductSchema:
    """
    Complete product schema with field mapping for CSV/JSON inputs.
    Maps various field name variations to standardized database columns.
    """
    
    # Core required fields for basic operations
    CORE_REQUIRED = ['sku', 'name']
    
    # Required fields for AI/ML forecasting
    AI_REQUIRED = [
        'sku', 'name', 'current_stock', 'unit_cost', 'unit_price', 
        'lead_time_days'
    ]
    
    # Fields critical for accurate demand forecasting
    FORECASTING_IMPORTANT = [
        'average_daily_demand', 'seasonality_factor', 'demand_volatility',
        'abc_classification', 'xyz_classification', 'inventory_turnover'
    ]
    
    # All optional extended fields
    OPTIONAL_FIELDS = [
        'category', 'reorder_point', 'safety_stock', 'supplier_id',
        'min_order_qty', 'max_order_qty', 'order_frequency_days',
        'profit_margin', 'product_priority', 'weight_kg', 'volume_m3',
        'shelf_life_days', 'is_perishable', 'is_hazardous',
        'storage_cost_per_unit', 'stockout_cost_per_unit',
        'target_service_level', 'economic_order_qty', 'weeks_of_supply',
        'stock_status', 'last_order_date', 'last_sale_date', 'description'
    ]
    
    # Field name aliases for flexible mapping (JSON key -> Database column)
    FIELD_ALIASES = {
        # Core fields
        'id': 'sku',
        'product_id': 'sku',
        'product_code': 'sku',
        'code': 'sku',
        'item_code': 'sku',
        'product_name': 'name',
        'title': 'name',
        'description': 'name',
        'item_name': 'name',
        
        # Stock and inventory
        'stock': 'current_stock',
        'inventory': 'current_stock',
        'quantity': 'current_stock',
        'qty': 'current_stock',
        'stock_level': 'current_stock',
        'on_hand': 'current_stock',
        
        # Pricing
        'cost': 'unit_cost',
        'cost_price': 'unit_cost',
        'purchase_price': 'unit_cost',
        'price': 'unit_price',
        'selling_price': 'unit_price',
        'retail_price': 'unit_price',
        'sale_price': 'unit_price',
        
        # Lead time
        'lead_time': 'lead_time_days',
        'leadtime': 'lead_time_days',
        'delivery_days': 'lead_time_days',
        
        # Classification
        'type': 'category',
        'product_type': 'category',
        'product_category': 'category',
        'class': 'abc_classification',
        'abc': 'abc_classification',
        'xyz': 'xyz_classification',
        'priority': 'product_priority',
        
        # Demand metrics
        'daily_demand': 'average_daily_demand',
        'avg_demand': 'average_daily_demand',
        'demand': 'average_daily_demand',
        'seasonality': 'seasonality_factor',
        'volatility': 'demand_volatility',
        'variability': 'demand_volatility',
        'turnover': 'inventory_turnover',
        
        # Physical attributes
        'weight': 'weight_kg',
        'volume': 'volume_m3',
        'shelf_life': 'shelf_life_days',
        'perishable': 'is_perishable',
        'hazardous': 'is_hazardous',
        
        # Costs
        'storage_cost': 'storage_cost_per_unit',
        'holding_cost': 'storage_cost_per_unit',
        'stockout_cost': 'stockout_cost_per_unit',
        'shortage_cost': 'stockout_cost_per_unit',
        
        # Supplier
        'supplier': 'supplier_id',
        'vendor': 'supplier_id',
        'vendor_id': 'supplier_id',
        
        # Order quantities
        'min_order': 'min_order_qty',
        'min_qty': 'min_order_qty',
        'max_order': 'max_order_qty',
        'max_qty': 'max_order_qty',
        'eoq': 'economic_order_qty',
        
        # Other
        'service_level': 'target_service_level',
        'status': 'stock_status',
    }
    
    # Field data types for validation and conversion
    FIELD_TYPES = {
        # String fields
        'sku': str,
        'name': str,
        'category': str,
        'supplier_id': str,
        'abc_classification': str,
        'xyz_classification': str,
        'product_priority': str,
        'stock_status': str,
        'description': str,
        
        # Integer fields
        'current_stock': int,
        'lead_time_days': int,
        'min_order_qty': int,
        'max_order_qty': int,
        'shelf_life_days': int,
        'order_frequency_days': int,
        
        # Float fields
        'unit_cost': float,
        'unit_price': float,
        'reorder_point': float,
        'safety_stock': float,
        'average_daily_demand': float,
        'seasonality_factor': float,
        'demand_volatility': float,
        'profit_margin': float,
        'weight_kg': float,
        'volume_m3': float,
        'storage_cost_per_unit': float,
        'stockout_cost_per_unit': float,
        'target_service_level': float,
        'economic_order_qty': float,
        'inventory_turnover': float,
        'weeks_of_supply': float,
        
        # Boolean fields
        'is_perishable': bool,
        'is_hazardous': bool,
        
        # DateTime fields
        'last_order_date': datetime,
        'last_sale_date': datetime,
    }
    
    # Default values for missing fields
    FIELD_DEFAULTS = {
        'category': 'General',
        'current_stock': 0,
        'unit_cost': 10.0,
        'unit_price': 15.0,
        'lead_time_days': 7,
        'seasonality_factor': 1.0,
        'demand_volatility': 0.5,
        'target_service_level': 0.95,
        'is_perishable': False,
        'is_hazardous': False,
    }


# ============================================================================
# SALES HISTORY SCHEMA DEFINITION
# ============================================================================

class SalesSchema:
    """
    Sales history schema with field mapping for CSV/JSON inputs.
    Supports both basic and enhanced sales data formats.
    """
    
    # Core required fields
    CORE_REQUIRED = ['date', 'sku', 'quantity_sold']
    
    # Required for revenue analysis
    REVENUE_REQUIRED = ['date', 'sku', 'quantity_sold', 'revenue']
    
    # Required for profit/loss analysis
    PROFIT_REQUIRED = [
        'date', 'sku', 'quantity_sold', 'revenue',
        'unit_price_at_sale', 'unit_cost_at_sale'
    ]
    
    # All optional enhanced fields
    OPTIONAL_FIELDS = [
        'revenue', 'unit_price_at_sale', 'unit_cost_at_sale',
        'profit_loss_amount', 'profit_margin_pct', 'discount_applied',
        'transaction_type', 'promotion_id', 'sales_channel',
        'customer_id', 'region'
    ]
    
    # Field name aliases
    FIELD_ALIASES = {
        # Core fields
        'sale_date': 'date',
        'transaction_date': 'date',
        'order_date': 'date',
        'product_sku': 'sku',
        'product_id': 'sku',
        'item_id': 'sku',
        'quantity': 'quantity_sold',
        'qty_sold': 'quantity_sold',
        'units_sold': 'quantity_sold',
        'qty': 'quantity_sold',
        
        # Revenue and pricing
        'sales': 'revenue',
        'total_sales': 'revenue',
        'amount': 'revenue',
        'total_amount': 'revenue',
        'unit_price': 'unit_price_at_sale',
        'price': 'unit_price_at_sale',
        'selling_price': 'unit_price_at_sale',
        'unit_cost': 'unit_cost_at_sale',
        'cost': 'unit_cost_at_sale',
        
        # Profit metrics
        'profit': 'profit_loss_amount',
        'profit_amount': 'profit_loss_amount',
        'profit_margin': 'profit_margin_pct',
        'margin': 'profit_margin_pct',
        
        # Discounts and promotions
        'discount': 'discount_applied',
        'discount_pct': 'discount_applied',
        'promo_id': 'promotion_id',
        'campaign_id': 'promotion_id',
        'transaction': 'transaction_type',
        'sale_type': 'transaction_type',
        
        # Channel and customer
        'channel': 'sales_channel',
        'customer': 'customer_id',
        'customer_code': 'customer_id',
        'location': 'region',
        'area': 'region',
    }
    
    # Field data types
    FIELD_TYPES = {
        'date': datetime,
        'sku': str,
        'quantity_sold': int,
        'revenue': float,
        'unit_price_at_sale': float,
        'unit_cost_at_sale': float,
        'profit_loss_amount': float,
        'profit_margin_pct': float,
        'discount_applied': float,
        'transaction_type': str,
        'promotion_id': str,
        'sales_channel': str,
        'customer_id': str,
        'region': str,
    }
    
    # Default values
    FIELD_DEFAULTS = {
        'revenue': 0.0,
        'transaction_type': 'Normal',
    }


# ============================================================================
# DATA MAPPER AND VALIDATOR
# ============================================================================

class DataMapper:
    """
    Unified data mapper for converting CSV/JSON inputs to standardized format.
    Handles field mapping, validation, type conversion, and missing values.
    """
    
    @staticmethod
    def map_field_names(data: Union[pd.DataFrame, Dict[str, Any]], 
                       schema: Union[ProductSchema, SalesSchema],
                       data_type: str = 'product') -> Union[pd.DataFrame, Dict[str, Any]]:
        """
        Map field names from various formats to standardized database columns.
        
        Args:
            data: Input data (DataFrame or dict)
            schema: Schema definition (ProductSchema or SalesSchema)
            data_type: 'product' or 'sales'
            
        Returns:
            Mapped data with standardized column names
        """
        is_dataframe = isinstance(data, pd.DataFrame)
        
        if is_dataframe:
            # DataFrame processing
            mapped_df = data.copy()
            columns_to_rename = {}
            
            for col in data.columns:
                col_lower = col.lower().strip()
                # Check if column needs mapping
                if col_lower in schema.FIELD_ALIASES:
                    target_col = schema.FIELD_ALIASES[col_lower]
                    columns_to_rename[col] = target_col
                elif col_lower != col:
                    # Normalize column name to lowercase
                    columns_to_rename[col] = col_lower
            
            if columns_to_rename:
                mapped_df = mapped_df.rename(columns=columns_to_rename)
            
            return mapped_df
        else:
            # Dictionary processing
            mapped_dict = {}
            for key, value in data.items():
                key_lower = key.lower().strip()
                # Map to standard field name
                if key_lower in schema.FIELD_ALIASES:
                    target_key = schema.FIELD_ALIASES[key_lower]
                    mapped_dict[target_key] = value
                else:
                    mapped_dict[key_lower] = value
            
            return mapped_dict
    
    @staticmethod
    def validate_required_fields(data: Union[pd.DataFrame, Dict[str, Any]],
                                required_fields: List[str],
                                data_type: str = 'product') -> Tuple[bool, List[str]]:
        """
        Validate that all required fields are present.
        
        Args:
            data: Input data
            required_fields: List of required field names
            data_type: 'product' or 'sales'
            
        Returns:
            (is_valid, missing_fields)
        """
        if isinstance(data, pd.DataFrame):
            available_fields = set(data.columns)
        else:
            available_fields = set(data.keys())
        
        missing = [f for f in required_fields if f not in available_fields]
        return (len(missing) == 0, missing)
    
    @staticmethod
    def convert_types(data: Union[pd.DataFrame, Dict[str, Any]],
                     field_types: Dict[str, type],
                     defaults: Dict[str, Any] = None) -> Union[pd.DataFrame, Dict[str, Any]]:
        """
        Convert field types and handle missing values.
        
        Args:
            data: Input data
            field_types: Field name to type mapping
            defaults: Default values for missing fields
            
        Returns:
            Data with converted types
        """
        defaults = defaults or {}
        is_dataframe = isinstance(data, pd.DataFrame)
        
        if is_dataframe:
            result_df = data.copy()
            
            for field, dtype in field_types.items():
                if field not in result_df.columns:
                    # Add missing field with default value
                    if field in defaults:
                        result_df[field] = defaults[field]
                    continue
                
                try:
                    if dtype == datetime:
                        result_df[field] = pd.to_datetime(result_df[field], errors='coerce')
                    elif dtype == bool:
                        # Handle various boolean representations
                        result_df[field] = result_df[field].apply(
                            lambda x: bool(x) if not isinstance(x, str) 
                            else x.lower() in ('true', '1', 'yes', 'y')
                        )
                    elif dtype == int:
                        result_df[field] = pd.to_numeric(result_df[field], errors='coerce').fillna(
                            defaults.get(field, 0)
                        ).astype(int)
                    elif dtype == float:
                        result_df[field] = pd.to_numeric(result_df[field], errors='coerce').fillna(
                            defaults.get(field, 0.0)
                        )
                    elif dtype == str:
                        result_df[field] = result_df[field].astype(str).str.strip()
                except Exception as e:
                    print(f"Warning: Could not convert field '{field}' to {dtype.__name__}: {e}")
            
            return result_df
        else:
            # Dictionary processing
            result_dict = data.copy()
            
            for field, dtype in field_types.items():
                if field not in result_dict:
                    if field in defaults:
                        result_dict[field] = defaults[field]
                    continue
                
                try:
                    value = result_dict[field]
                    if value is None:
                        result_dict[field] = defaults.get(field)
                        continue
                    
                    if dtype == datetime:
                        if isinstance(value, str):
                            result_dict[field] = pd.to_datetime(value)
                        elif isinstance(value, datetime):
                            result_dict[field] = value
                    elif dtype == bool:
                        if isinstance(value, str):
                            result_dict[field] = value.lower() in ('true', '1', 'yes', 'y')
                        else:
                            result_dict[field] = bool(value)
                    elif dtype == int:
                        result_dict[field] = int(float(value))
                    elif dtype == float:
                        result_dict[field] = float(value)
                    elif dtype == str:
                        result_dict[field] = str(value).strip()
                except Exception as e:
                    print(f"Warning: Could not convert field '{field}' to {dtype.__name__}: {e}")
                    result_dict[field] = defaults.get(field)
            
            return result_dict
    
    @staticmethod
    def prepare_product_data(data: Union[pd.DataFrame, Dict[str, Any], List[Dict[str, Any]]],
                           validate_ai_fields: bool = False) -> Union[pd.DataFrame, Dict[str, Any], List[Dict[str, Any]]]:
        """
        Complete pipeline: map, validate, and convert product data.
        
        Args:
            data: Raw input data (DataFrame, dict, or list of dicts)
            validate_ai_fields: If True, require AI/forecasting fields
            
        Returns:
            Processed data ready for database insertion
            
        Raises:
            ValueError: If required fields are missing
        """
        schema = ProductSchema()
        
        # Handle list of dictionaries
        if isinstance(data, list):
            return [DataMapper.prepare_product_data(item, validate_ai_fields) for item in data]
        
        # Step 1: Map field names
        mapped_data = DataMapper.map_field_names(data, schema, 'product')
        
        # Step 2: Validate required fields
        required = schema.AI_REQUIRED if validate_ai_fields else schema.CORE_REQUIRED
        is_valid, missing = DataMapper.validate_required_fields(mapped_data, required, 'product')
        
        if not is_valid:
            raise ValueError(f"Missing required product fields: {', '.join(missing)}")
        
        # Step 3: Convert types and apply defaults
        processed_data = DataMapper.convert_types(
            mapped_data,
            schema.FIELD_TYPES,
            schema.FIELD_DEFAULTS
        )
        
        return processed_data
    
    @staticmethod
    def prepare_sales_data(data: Union[pd.DataFrame, Dict[str, Any], List[Dict[str, Any]]],
                          require_profit_fields: bool = False) -> Union[pd.DataFrame, Dict[str, Any], List[Dict[str, Any]]]:
        """
        Complete pipeline: map, validate, and convert sales data.
        
        Args:
            data: Raw input data
            require_profit_fields: If True, require profit/loss fields
            
        Returns:
            Processed data ready for database insertion
            
        Raises:
            ValueError: If required fields are missing
        """
        schema = SalesSchema()
        
        # Handle list of dictionaries
        if isinstance(data, list):
            return [DataMapper.prepare_sales_data(item, require_profit_fields) for item in data]
        
        # Step 1: Map field names
        mapped_data = DataMapper.map_field_names(data, schema, 'sales')
        
        # Step 2: Validate required fields
        required = schema.PROFIT_REQUIRED if require_profit_fields else schema.CORE_REQUIRED
        is_valid, missing = DataMapper.validate_required_fields(mapped_data, required, 'sales')
        
        if not is_valid:
            raise ValueError(f"Missing required sales fields: {', '.join(missing)}")
        
        # Step 3: Convert types and apply defaults
        processed_data = DataMapper.convert_types(
            mapped_data,
            schema.FIELD_TYPES,
            schema.FIELD_DEFAULTS
        )
        
        # Step 4: Calculate derived fields if possible
        if isinstance(processed_data, pd.DataFrame):
            if 'unit_price_at_sale' in processed_data.columns and 'unit_cost_at_sale' in processed_data.columns:
                # Calculate profit if not present
                if 'profit_loss_amount' not in processed_data.columns or processed_data['profit_loss_amount'].isna().all():
                    processed_data['profit_loss_amount'] = (
                        (processed_data['unit_price_at_sale'] - processed_data['unit_cost_at_sale']) *
                        processed_data['quantity_sold']
                    )
                
                # Calculate profit margin if not present
                if 'profit_margin_pct' not in processed_data.columns or processed_data['profit_margin_pct'].isna().all():
                    processed_data['profit_margin_pct'] = (
                        (processed_data['unit_price_at_sale'] - processed_data['unit_cost_at_sale']) /
                        processed_data['unit_price_at_sale'] * 100
                    ).fillna(0)
        elif isinstance(processed_data, dict):
            if 'unit_price_at_sale' in processed_data and 'unit_cost_at_sale' in processed_data:
                if 'profit_loss_amount' not in processed_data:
                    processed_data['profit_loss_amount'] = (
                        (processed_data['unit_price_at_sale'] - processed_data['unit_cost_at_sale']) *
                        processed_data['quantity_sold']
                    )
                if 'profit_margin_pct' not in processed_data:
                    processed_data['profit_margin_pct'] = (
                        (processed_data['unit_price_at_sale'] - processed_data['unit_cost_at_sale']) /
                        processed_data['unit_price_at_sale'] * 100
                    ) if processed_data['unit_price_at_sale'] > 0 else 0
        
        return processed_data


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_forecasting_features(product_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract features required for demand forecasting from product data.
    
    Args:
        product_data: Product information dictionary
        
    Returns:
        Dictionary with forecasting-relevant features
    """
    schema = ProductSchema()
    features = {}
    
    # Core forecasting features
    for field in schema.FORECASTING_IMPORTANT:
        if field in product_data:
            features[field] = product_data[field]
    
    # Additional useful fields
    additional = ['current_stock', 'reorder_point', 'safety_stock', 'lead_time_days']
    for field in additional:
        if field in product_data:
            features[field] = product_data[field]
    
    return features


def validate_data_quality(data: pd.DataFrame, data_type: str = 'product') -> Dict[str, Any]:
    """
    Validate data quality and return diagnostics.
    
    Args:
        data: DataFrame to validate
        data_type: 'product' or 'sales'
        
    Returns:
        Dictionary with validation results and warnings
    """
    results = {
        'is_valid': True,
        'warnings': [],
        'errors': [],
        'stats': {}
    }
    
    # Check for duplicates
    if data_type == 'product' and 'sku' in data.columns:
        duplicates = data['sku'].duplicated().sum()
        if duplicates > 0:
            results['warnings'].append(f"Found {duplicates} duplicate SKUs")
            results['stats']['duplicate_skus'] = duplicates
    
    # Check for missing values in critical fields
    schema = ProductSchema() if data_type == 'product' else SalesSchema()
    required = schema.AI_REQUIRED if data_type == 'product' else schema.CORE_REQUIRED
    
    for field in required:
        if field in data.columns:
            missing = data[field].isna().sum()
            if missing > 0:
                results['warnings'].append(f"Field '{field}' has {missing} missing values")
    
    now = datetime.now()

    # Check data ranges
    if data_type == 'product':
        if 'current_stock' in data.columns:
            negative_stock = (data['current_stock'] < 0).sum()
            if negative_stock > 0:
                results['errors'].append(f"Found {negative_stock} products with negative stock")
                results['is_valid'] = False
        if 'unit_cost' in data.columns:
            negative_cost = (data['unit_cost'] < 0).sum()
            if negative_cost > 0:
                results['errors'].append(f"{negative_cost} products have negative unit_cost")
                results['is_valid'] = False
        if 'unit_price' in data.columns:
            negative_price = (data['unit_price'] <= 0).sum()
            if negative_price > 0:
                results['warnings'].append(f"{negative_price} products have non-positive selling price")
            below_cost = ((data['unit_price'] < data['unit_cost']) & data['unit_cost'].notna()).sum()
            if below_cost > 0:
                results['warnings'].append(f"{below_cost} products sell below cost (verify pricing)")
        if 'lead_time_days' in data.columns:
            invalid_lead = (data['lead_time_days'] < 0).sum()
            if invalid_lead > 0:
                results['errors'].append(f"{invalid_lead} products have negative lead times")
                results['is_valid'] = False
        if 'target_service_level' in data.columns:
            invalid_sl = ((data['target_service_level'] <= 0) | (data['target_service_level'] > 1)).sum()
            if invalid_sl > 0:
                results['warnings'].append(f"{invalid_sl} products have target_service_level outside 0-1 range")
    else:
        if 'quantity_sold' in data.columns:
            negative_qty = (data['quantity_sold'] < 0).sum()
            if negative_qty > 0:
                results['errors'].append(f"{negative_qty} sales rows have negative quantity_sold")
                results['is_valid'] = False
        if 'date' in data.columns:
            dates = pd.to_datetime(data['date'], errors='coerce')
            future_dates = (dates > now).sum()
            if future_dates > 0:
                results['warnings'].append(f"{future_dates} sales rows have future transaction dates")
        if {'unit_price_at_sale', 'unit_cost_at_sale'}.issubset(data.columns):
            margin_issues = ((data['unit_price_at_sale'] < data['unit_cost_at_sale']) & data['unit_price_at_sale'].notna()).sum()
            if margin_issues > 0:
                results['warnings'].append(f"{margin_issues} sales rows are priced below cost")
    
    results['stats']['total_records'] = len(data)
    results['stats']['columns'] = list(data.columns)
    
    return results
